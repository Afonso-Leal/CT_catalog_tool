#!/usr/bin/env python3
"""
Script para selecionar e analisar amostras de CTs do ct_search_report.json
"""

import json
import sys
from pathlib import Path

CT_CANDIDATES = [
    "https://www.institutonovavida.org/casas-de-recuperacao-de-dependentes-quimicos-evangelicas",
    "https://casadiasp.com.br/",
    "https://crenvi.org.br/",
    "https://www.clinicasviverbem.com/clinica-de-recuperacao-em-curitiba-pr/",
    "https://clinicavivavida.com/clinicas/550/boqueirao-curitiba-pr",
    "https://www.gruporecanto.com.br/",
    "https://www.gruponovavida.com.br/clinicas-de-recuperacao/curitiba-pr",
    "https://gruporecomeco.com.br/",
    "https://crejer.org.br/",
    "https://www.institutogratidao.org/",
]


def load_ct_search_report(path: str = "../ct_search_report.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_cts_from_report(report: list[dict], candidates: list[str]) -> list[dict]:
    urls = set(candidates)
    return [item for item in report if item.get("link") in urls]


def main():
    print("Carregando relatório de busca...")
    report = load_ct_search_report()

    print(f"Total de URLs no relatório: {len(report)}")

    cts = filter_cts_from_report(report, CT_CANDIDATES)
    print(f"CTs encontradas no relatório: {len(cts)}")

    for ct in cts:
        print(f"  - {ct['title'][:60]}...")
        print(f"    {ct['link']}")

    output_path = Path("output/sample_cts_10.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cts, f, ensure_ascii=False, indent=2)

    print(f"\nLista salva em: {output_path}")


if __name__ == "__main__":
    main()
