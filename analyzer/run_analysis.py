#!/usr/bin/env python3
"""
Run Analysis - Executa análise de CTs usando o analyzer
"""

import json
from pathlib import Path
from analyzer.ct_analyzer import (
    CTAnalyzer,
    save_result_json,
    save_result_md,
    AnalysisResult,
    Classification,
)
from datetime import datetime


def load_ct_contents(path: str = "analyzer/output/ct_contents.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cts_sample(path: str = "analyzer/output/sample_cts_10.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_analysis():
    print("Inicializando analyzer...")
    analyzer = CTAnalyzer()
    print(f"Provider: {analyzer.llm.provider}, Model: {analyzer.llm.model}")

    contents = load_ct_contents()
    sample = load_cts_sample()

    sample_dict = {ct["link"]: ct.get("title", "") for ct in sample}

    seen_urls = set()
    unique_contents = []
    for c in contents:
        if c["url"] not in seen_urls and c.get("content"):
            seen_urls.add(c["url"])
            unique_contents.append(c)

    print(f"\nAnalisando {len(unique_contents)} CTs (únicas)...")

    results = []
    for i, ct_content in enumerate(unique_contents):
        url = ct_content["url"]
        content = ct_content.get("content", "")
        titulo = sample_dict.get(url, "")

        print(f"\n[{i + 1}/{len(unique_contents)}] Analisando: {titulo[:50]}...")
        print(f"  URL: {url[:60]}...")

        if not content:
            print(f"  ⚠️ Sem conteúdo para analisar")
            result = AnalysisResult(
                url=url,
                titulo=titulo,
                classificacao=Classification.INCONCLUSIVO,
                score_confianca=0.0,
                findings=[],
                resumo="Sem conteúdo disponível para análise",
            )
        else:
            result = analyzer.analyze(url, content, titulo)

        print(f"  Classificação: {result.classificacao.value}")
        print(f"  Score: {result.score_confianca:.0%}")
        print(f"  Findings: {len(result.findings)}")

        results.append(result)

    return results


def run_analysis_bulk(n: int, contents_path: str = "analyzer/output/ct_contents.json") -> list[AnalysisResult]:
    """
    Analisa em lote as primeiras `n` entradas (únicas) de `ct_contents.json` que tenham conteúdo.

    Usado pelo TUI como comando "analyze bulk".
    """

    n = int(n)
    if n <= 0:
        return []

    print("Inicializando analyzer...")
    analyzer = CTAnalyzer()
    print(f"Provider: {analyzer.llm.provider}, Model: {analyzer.llm.model}")

    contents = load_ct_contents(contents_path)

    seen_urls = set()
    selected: list[dict] = []
    for c in contents:
        url = c.get("url")
        if not url or url in seen_urls:
            continue
        if not c.get("content"):
            continue
        seen_urls.add(url)
        selected.append(c)
        if len(selected) >= n:
            break

    print(f"\nAnalisando {len(selected)} CTs (amostra n={n})...")

    results: list[AnalysisResult] = []
    for i, ct_content in enumerate(selected):
        url = ct_content["url"]
        content = ct_content.get("content", "")

        print(f"\n[{i + 1}/{len(selected)}] URL: {url[:80]}...")
        result = analyzer.analyze(url, content, titulo="")

        print(f"  Classificação: {result.classificacao.value}")
        print(f"  Score: {result.score_confianca:.0%}")
        print(f"  Findings: {len(result.findings)}")

        results.append(result)

    return results


def save_all_results(results: list[AnalysisResult]):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"analyzer/output/analysis_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    for result in results:
        save_result_json(result, output_dir / f"{hash(result.url)}.json")
        save_result_md(result, output_dir / f"{hash(result.url)}.md")

        all_results.append(
            {
                "url": result.url,
                "titulo": result.titulo,
                "classificacao": result.classificacao.value,
                "score_confianca": result.score_confianca,
                "findings_count": len(result.findings),
                "resumo": result.resumo,
            }
        )

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    summary_md = output_dir / "summary.md"
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write("# Resumo da Análise de Comunidades Terapêuticas\n\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("## Resultados\n\n")
        for r in all_results:
            emoji = (
                "🔴"
                if r["classificacao"] == "SUSPEITA"
                else "🟢"
                if r["classificacao"] == "NÃO_SUSPEITA"
                else "⚪"
            )
            f.write(f"- {emoji} **{r['titulo'][:60]}**\n")
            f.write(f"  - URL: {r['url']}\n")
            f.write(
                f"  - Classificação: {r['classificacao']} ({r['score_confianca']:.0%})\n"
            )
            f.write(f"  - Findings: {r['findings_count']}\n")
            f.write(f"  - Resumo: {r['resumo'][:100]}...\n\n")

    print(f"\nResultados salvos em: {output_dir}")
    return output_dir


def main():
    results = run_analysis()
    output_dir = save_all_results(results)

    print(f"\n{'=' * 60}")
    print("ANÁLISE CONCLUÍDA")
    print(f"{'=' * 60}")

    from collections import Counter

    classes = Counter(r.classificacao.value for r in results)
    print(f"\nDistribuição de classificações:")
    for cls, count in classes.items():
        print(f"  {cls}: {count}")

    print(f"\nResumo: {output_dir}/summary.md")


if __name__ == "__main__":
    main()
