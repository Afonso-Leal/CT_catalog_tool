#!/usr/bin/env python3
"""
Fetcher - Extrai conteúdo HTML de URLs de CTs
Usa requests + scrapling/beautifulsoup
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
from time import sleep


def fetch_ct_content(url: str, timeout: int = 30) -> dict:
    """Busca conteúdo de uma URL de CT."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line.strip())

        return {
            "url": url,
            "status_code": response.status_code,
            "content": text[:20000],
            "content_length": len(text),
        }
    except Exception as e:
        return {"url": url, "error": str(e), "content": "", "content_length": 0}


def fetch_batch(urls: list[str], delay: float = 1.0) -> list[dict]:
    """Busca conteúdo de múltiplas URLs."""
    results = []
    for i, url in enumerate(urls):
        print(f"[{i + 1}/{len(urls)}] Fetching: {url[:60]}...")
        result = fetch_ct_content(url)
        results.append(result)
        if i < len(urls) - 1:
            sleep(delay)
    return results


def load_cts_sample(path: str = "analyzer/output/sample_cts_10.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    cts = load_cts_sample()
    urls = [ct["link"] for ct in cts]

    print(f"Buscando conteúdo de {len(urls)} CTs...")
    results = fetch_batch(urls)

    output_path = Path("output/ct_contents.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nConteúdo salvo em: {output_path}")
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['url'][:50]}... - {r['error'][:30]}")
        else:
            print(f"  ✅ {r['url'][:50]}... ({r['content_length']} chars)")


if __name__ == "__main__":
    main()
