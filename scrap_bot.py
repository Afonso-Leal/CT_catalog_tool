"""
Scrap Bot - Website analysis using LLM and MCP tools
"""

import json
from call_llm import LLMWrapper
from tools_templates import fetch_url_content
from local_rag import (
    extract_focus_terms,
    load_kb_chunks_md,
    retrieve_kb,
    select_relevant_text,
)


KB_PATH = "DATABASE_LEGISLACAO_COMUNIDADES_TERAPÊUTICAS_BRASIL.md"


def ler_json(caminho_arquivo: str) -> dict:
    """Read JSON file."""
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_json_em_arquivo(variavel_json, caminho_arquivo: str):
    """Save JSON to file."""
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(variavel_json, arquivo, indent=2, ensure_ascii=False)


def call_to_scrap_site(site_info: dict, dados_pdf: dict) -> str:
    """
    Analyze if a website is a therapeutic center.
    """
    url = site_info.get("link", "")
    titulo = site_info.get("title", "")

    # Integração com `search_tool.py`: se já vier `content`, usamos; senão baixamos via template.
    content = site_info.get("content")
    if not isinstance(content, str) or not content.strip():
        fetched = fetch_url_content(url, timeout=30)
        content = fetched.get("content", "")

    # Selecionar apenas os ~15k caracteres mais relevantes do site.
    focus_terms = extract_focus_terms(
        dados_pdf.get("lista_de_caracteristicas_gerais_cts", []),
        dados_pdf.get("lista_de_regras_que_devem_seguir", []),
        limit=60,
    )
    relevant_site_text = select_relevant_text(
        site_text=str(content),
        focus_terms=focus_terms,
        max_chars=15000,
    )

    # RAG local: recuperar trechos mais similares da KB (base pequena).
    kb_chunks = load_kb_chunks_md(KB_PATH)
    kb_hits = retrieve_kb(kb_chunks, query_text=relevant_site_text, top_k=5, max_chunk_chars=1200)
    kb_section = "\n\n".join(
        [
            f"[{c.chunk_id}] {c.title}\n{c.text}"
            for c in kb_hits
        ]
    ).strip()

    pergunta = f"""
    Você é um psicólogo responsável por catalogar centros terapêuticos legais e ilegais presentes em diversos sites na internet.
    Tem a tarefa de analisar o site (URL: {url} | título: {titulo}) usando APENAS o conteúdo abaixo.

    Baseado nesta lista de características gerais de centros terapêuticos:
    {dados_pdf["lista_de_caracteristicas_gerais_cts"]}

    Você deve identificar, após uma investigação minuciosa no site, se ele atende às características para ser considerado um centro terapêutico.
    Salve quais características o site possui em uma variável `caracteristicas_CTS_tem`.

    Você também deve utilizar a seguinte lista de regras que centros terapêuticos devem seguir:
    {dados_pdf["lista_de_regras_que_devem_seguir"]}

    E deve elencar em quais regras não seguem, salvando em uma lista `regras_CTS_n_seguem`.

    Regras IMPORTANTES:
    - Não invente. Só inclua um item se houver evidência explícita no conteúdo.
    - Para cada item retornado, inclua um trecho literal do site entre aspas dentro da string.
      Ex.: "Regra X — evidência: \"...trecho...\""
    - Se não houver evidência suficiente, retorne listas vazias (não use textos fora do JSON).
    - Use os trechos da BASE LEGAL (abaixo) apenas como referência para enquadramento; a evidência sempre
      deve vir do conteúdo do site.

    Cada um dos valores do JSON deverá ser uma lista de strings. Exemplo:
    {{
        "caracteristicas_CTS_tem": ["recolhem pessoas para recuperação", "tratam de dependencia"],
        "regras_CTS_n_seguem": ["nao podem internar por mais de 90 dias", "devem ser regulamentados"]
    }}

    Retorne APENAS o JSON válido (sem markdown, sem texto antes/depois).

    CONTEÚDO DO SITE (trechos mais relevantes, até 15k chars):
    {relevant_site_text}

    BASE LEGAL (top-5 trechos similares por busca local):
    {kb_section if kb_section else "(sem hits relevantes)"}
    """

    # Initialize LLM
    llm = LLMWrapper()

    # Create initial message
    messages = [{"role": "user", "content": pergunta}]

    response = llm.chat(messages, temperature=0.1, max_tokens=2048)
    return response.content


if __name__ == "__main__":
    dados_search = ler_json("./ct_search_report.json")
    dados_pdf = ler_json("./ct_report.json")

    resultados = []
    for search in dados_search:
        print()
        resultado = call_to_scrap_site(search, dados_pdf)
        if resultado:
            resultados.append(resultado)
        print(resultados)
        break  # Test only first item
