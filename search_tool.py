"""
Search Tool - Web search and scraping
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from scrapling.fetchers import StealthyFetcher
from lxml import html as lxml_html
from read_pdf import salvar_json_em_arquivo
from tools_templates import fetch_url_content


def tool_search_brave(
    query: str,
    max_pages: int = 1,
    max_results: int = 20,
) -> list[dict]:
    """Tool: busca no Brave e retorna lista de resultados."""

    results = buscar_google_sync(query, max_pages)
    return results[:max_results]


def tool_fetch_url(
    url: str,
    timeout: int = 30,
) -> dict:
    """Tool: baixa uma URL e retorna conteúdo limpo/erro."""

    return fetch_url_content(url, timeout=timeout)


def tool_search_brave_with_content(
    query: str,
    max_pages: int = 1,
    max_results: int = 20,
    max_fetch: int = 3,
    timeout: int = 30,
) -> list[dict]:
    """
    Tool: busca no Brave e enriquece os primeiros resultados com `content`.
    """

    results = buscar_google_sync(query, max_pages)[:max_results]
    return enriquecer_com_conteudo(results, max_itens=max_fetch, timeout=timeout)


def tool_save_search_report_md(
    output_path: str,
    queries: list[str],
    results: list[dict],
    max_preview_chars: int = 600,
) -> str:
    """Tool: salva relatório Markdown e retorna o caminho."""

    return salvar_markdown_busca(
        output_path=output_path,
        queries=queries,
        resultados=results,
        max_preview_chars=max_preview_chars,
    )


def ler_json(caminho_arquivo: str) -> dict:
    """Lê um arquivo JSON e retorna seu conteúdo como dicionário."""
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não é um JSON válido.")
        return None
    except Exception as e:
        print(f"Erro inesperado ao ler o arquivo: {e}")
        return None


def buscar_google_sync(search: str, max_pg: int = 1) -> list[dict]:
    """Busca no Brave Search."""
    resultados = []

    for n_p in range(max_pg):
        url = f"https://search.brave.com/search?q={search}&offset={n_p}&spellcheck=0"
        # `network_idle=True` tende a demorar muito em páginas modernas;
        # como só precisamos do HTML do bloco `#results`, não vale esperar "idle".
        page = StealthyFetcher.fetch(url, headless=True, network_idle=False)

        try:
            all_html = page.xpath("//div[@id='results']")[0].html_content
        except IndexError:
            continue

        tree = lxml_html.fromstring(all_html)

        elementos = tree.xpath("//div[contains(@class, 'result-content')]/a")
        len_elementos = len(elementos)
        links = [elementos[i].get("href") for i in range(len_elementos)]

        elementos = tree.xpath(
            "//div[contains(@class, 'result-content')]/a/div[contains(@class, 'title search-snippet-title')]"
        )
        titulos = [elementos[i].text for i in range(len_elementos)]

        elementos = tree.xpath("//div[contains(@class,'snippet  ')]")
        iners = [
            lxml_html.tostring(elementos[i]).decode("utf-8")
            for i in range(len_elementos)
        ]

        tmp = [
            {"link": link, "title": title, "html": inner}
            for inner, title, link in zip(iners, titulos, links)
        ]
        resultados += tmp

    return resultados


def enriquecer_com_conteudo(
    resultados: list[dict], max_itens: int = 5, timeout: int = 30
) -> list[dict]:
    """
    Enriquecimento "template tool": baixa conteúdo das URLs para o `scrap_bot.py`.

    Adiciona as chaves:
    - content: texto limpo (até 20k chars)
    - content_length, status_code (quando disponível)
    - error (quando falhar)
    """

    enriquecidos: list[dict] = []
    for i, item in enumerate(resultados):
        if i >= max_itens:
            enriquecidos.append(item)
            continue

        url = item.get("link")
        if not url:
            enriquecidos.append(item)
            continue

        content_payload = fetch_url_content(url, timeout=timeout)
        merged = {**item, **content_payload}
        enriquecidos.append(merged)

    return enriquecidos


def salvar_markdown_busca(
    output_path: str | Path,
    queries: list[str],
    resultados: list[dict],
    max_preview_chars: int = 600,
) -> str:
    """Salva um relatório Markdown das buscas e resultados."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = []
    lines.append("# Relatório de busca (Brave)\n")
    lines.append(f"- Gerado em: **{ts}**\n")
    lines.append(f"- Total de queries: **{len(queries)}**\n")
    lines.append(f"- Total de resultados: **{len(resultados)}**\n")
    lines.append("\n## Queries\n")
    for q in queries:
        lines.append(f"- {q}")

    lines.append("\n\n## Resultados\n")
    for i, r in enumerate(resultados, start=1):
        title = (r.get("title") or "").strip()
        link = (r.get("link") or "").strip()
        snippet_html = (r.get("html") or "").strip()
        content_len = r.get("content_length")
        status_code = r.get("status_code")
        error = r.get("error")

        lines.append(f"\n### {i}. {title or '(sem título)'}\n")
        if link:
            lines.append(f"- **Link**: `{link}`")
        if status_code is not None:
            lines.append(f"- **Status**: {status_code}")
        if content_len is not None:
            lines.append(f"- **Content length**: {content_len}")
        if error:
            lines.append(f"- **Erro**: {error}")

        if snippet_html:
            preview = snippet_html[:max_preview_chars].replace("\n", " ").strip()
            lines.append(f"- **Snippet (HTML)**: `{preview}`")

        if isinstance(r.get("content"), str) and r["content"].strip():
            preview_txt = r["content"][:max_preview_chars].replace("\n", " ").strip()
            lines.append(f"- **Conteúdo (preview)**: `{preview_txt}`")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    print("Iniciando busca...")
    dados = ler_json("./ct_report.json")

    if dados is None:
        print("Erro: ct_report.json não encontrado")
        exit(1)

    sinonimos = dados.get("sinonimos_de_centro_terapeutico_para_pesquisar", [])

    if not sinonimos:
        print("Erro: sinonimos não encontrados no JSON")
        exit(1)

    resultados = []
    StealthyFetcher.adaptive = True

    for search in sinonimos:
        resultados += buscar_google_sync(search, 1)

    # Para integrar com o `scrap_bot.py` sem MCP: já baixamos conteúdo das primeiras URLs.
    resultados = enriquecer_com_conteudo(resultados, max_itens=5, timeout=30)
    salvar_json_em_arquivo(resultados, "./ct_search_report.json")
    print(f"Salvos {len(resultados)} resultados em ct_search_report.json")

    md_path = salvar_markdown_busca(
        "./ct_search_report.md", queries=sinonimos, resultados=resultados
    )
    print(f"Relatório Markdown salvo em: {md_path}")
