"""
Templates de ferramentas locais (sem MCP).

Objetivo: permitir que o pipeline `search_tool.py` -> `scrap_bot.py` funcione sem depender
de um servidor externo, apenas baixando conteúdo de URLs e retornando texto limpo.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def fetch_url_content(url: str, timeout: int = 30, max_chars: int = 20000) -> Dict[str, Any]:
    """
    Baixa uma URL e retorna um payload padronizado com HTML→texto limpo.

    Mantém compatibilidade com `analyzer.fetch_cts.fetch_ct_content` para evitar duplicação.
    """

    try:
        from analyzer.fetch_cts import fetch_ct_content  # type: ignore
    except Exception:
        fetch_ct_content = None  # type: ignore

    if fetch_ct_content:
        data = fetch_ct_content(url, timeout=timeout)
        # `fetch_ct_content` já corta `content` em 20000, mas garantimos.
        if "content" in data and isinstance(data["content"], str):
            data["content"] = data["content"][:max_chars]
        return data

    # Fallback ultra simples (caso analyzer/ não esteja disponível por algum motivo)
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"

    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = "\n".join(line for line in text.splitlines() if line.strip())

    return {
        "url": url,
        "status_code": r.status_code,
        "content": text[:max_chars],
        "content_length": len(text),
    }

