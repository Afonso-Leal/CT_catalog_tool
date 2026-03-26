"""
Módulo de Análise de Comunidades Terapêuticas
Usa LLM com base de conhecimento carregada no prompt
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum

from call_llm import LLMWrapper


KB_PATH = Path("DATABASE_LEGISLACAO_COMUNIDADES_TERAPÊUTICAS_BRASIL.md")


class Classification(Enum):
    SUSPEITA = "SUSPEITA"
    NAO_SUSPEITA = "NÃO_SUSPEITA"
    INCONCLUSIVO = "INCONCLUSIVO"


@dataclass
class Finding:
    modulo: str
    termo_encontrado: str
    trecho_exato: str
    violacao: str
    evidencia_ref: str


@dataclass
class AnalysisResult:
    url: str
    titulo: str
    classificacao: Classification
    score_confianca: float
    findings: list[Finding]
    resumo: str


CHECKLIST_VIOLACOES = {
    "religioso": [
        {
            "termo": "transformational program",
            "eufemismo": "programa transformacional baseado em fé",
            "violacao": "Proselitismo religioso coercitivo disfarçado de programa terapêutico",
            "ref": "Lei 13.840/2019, RDC 29/2011",
        },
        {
            "termo": "busca a Deus",
            "eufemismo": "busca espiritual/deus/fé",
            "violacao": "Utilização de conversão religiosa como parte do tratamento",
            "ref": "RDC 29/2011 - Princípio da laicidade",
        },
        {
            "termo": "evangélica",
            "eufemismo": "tratamento religioso",
            "violacao": "Instituição confessional que impõe credo como parte do tratamento",
            "ref": "RDC 29/2011 - Tipo: pública, privada, comunitária, confessional ou filantrópica",
        },
    ],
    "voluntariedade": [
        {
            "termo": "internação involuntária",
            "eufemismo": "internação compulsória, internação sem consentimento",
            "violacao": "Acolhimento involuntário - vedado pela Lei 11.343/2006 Art. 26-A",
            "ref": "Lei 11.343/2006 Art. 26-A IV",
        },
        {
            "termo": "contrato de permanência",
            "eufemismo": "permanência obrigatória, multa rescisória",
            "violacao": "Cláusula de permanência obrigatória viola princípio da voluntariedade",
            "ref": "RDC 29/2011 - Admissão mediante avaliação diagnóstica",
        },
        {
            "termo": "obrigatório",
            "eufemismo": "regra da casa, disciplina obrigatória",
            "violacao": "Regras obrigatórias podem indicar restrição à liberdade",
            "ref": "Lei 13.840/2019 Art. 23 - vedada privação de liberdade",
        },
    ],
    "trabalho": [
        {
            "termo": "laborterapia",
            "eufemismo": "tividade prática, terapia pelo trabalho",
            "violacao": "Trabalho forçado/explorado disfarçado de terapia - Lei 13.840/2019 Art. 23",
            "ref": "Lei 13.840/2019 Art. 23 - vedado trabalho forçado",
        },
        {
            "termo": "sem remuneração",
            "eufemismo": "trabalho voluntário, contrapartida",
            "violacao": "Exploração de trabalho não remunerado - Lei 13.840/2019 Art. 23 II",
            "ref": "Lei 13.840/2019 Art. 23 II - vedado trabalho sem remuneração",
        },
    ],
    "legal": [
        {
            "termo": "sem licença",
            "eufemismo": "sem alvará, sem licença sanitária",
            "violacao": "Funcionamento sem licença da Vigilância Sanitária - RDC 29/2011 Art. 3",
            "ref": "RDC 29/2011 Art. 3 - Licença de funcionamento obrigatória",
        },
        {
            "termo": "não registrado",
            "eufemismo": "sem responsável técnico",
            "violacao": "Instituição sem responsável técnico - RDC 29/2011 Art. 5",
            "ref": "RDC 29/2011 Art. 5 - Responsável técnico obrigatório",
        },
    ],
}


SYSTEM_PROMPT = """Você é um analisador especializado em Comunidades Terapêuticas (CTs) no Brasil.

Sua função é analisar o conteúdo de sites de CTs e identificar possíveis violações regulatórias.

## Base de Conhecimento - Legislação Brasileira sobre CTs:

{KB_CONTENT}

## Checklist de Violações a Identificar:

{CHECKLIST}

## Regras de Análise:

1. Analise o conteúdo do site fornecido
2. Identifique termos do checklist ou eufemismos relacionados
3. Classifique como:
   - SUSPEITA: encontrou violações claras (trabalho forçado, internação involuntária, proselitismo religioso coercitivo, funcionamento sem licença)
   - NÃO_SUSPEITA: não encontrou violações evidentes
   - INCONCLUSIVO: informações insuficientes para decidir

4. Retorne APENAS JSON válido neste formato exato, sem nenhum texto antes ou depois:
{{"classificacao": "SUSPEITA", "score_confianca": 0.85, "findings": [{{"modulo": "religioso", "termo_encontrado": "evangélica", "trecho_exato": "...", "violacao": "...", "evidencia_ref": "..."}}], "resumo": "..."}}

Não inclua markdown, não inclua código, não inclua explicações. Apenas o JSON puro."""


class CTAnalyzer:
    def __init__(self, kb_path: Optional[Path] = None):
        self.kb_path = kb_path or KB_PATH
        self.llm = LLMWrapper()
        self.kb_content = self._load_kb()

    def _load_kb(self) -> str:
        if self.kb_path.exists():
            return self.kb_path.read_text(encoding="utf-8")
        return ""

    def _build_checklist_text(self) -> str:
        lines = []
        for modulo, checks in CHECKLIST_VIOLACOES.items():
            lines.append(f"\n### {modulo.upper()}:")
            for c in checks:
                lines.append(
                    f"  - '{c['termo']}' ({c['eufemismo']}): {c['violacao']} [{c['ref']}]"
                )
        return "\n".join(lines)

    def _build_prompt(self, content: str) -> str:
        return SYSTEM_PROMPT.format(
            KB_CONTENT=self.kb_content[:8000], CHECKLIST=self._build_checklist_text()
        )

    def analyze(self, url: str, content: str, titulo: str = "") -> AnalysisResult:
        prompt = self._build_prompt(content)

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Analise este site:\n\nURL: {url}\nTítulo: {titulo}\n\nConteúdo:\n{content[:15000]}",
            },
        ]

        try:
            response = self.llm.chat(messages, temperature=0.1, max_tokens=2048)
            result = self._parse_response(response.content)
            result.url = url
            result.titulo = titulo
            return result
        except Exception as e:
            return AnalysisResult(
                url=url,
                titulo=titulo,
                classificacao=Classification.INCONCLUSIVO,
                score_confianca=0.0,
                findings=[],
                resumo=f"Erro na análise: {str(e)}",
            )

    def _parse_response(self, content: str) -> AnalysisResult:
        import re

        classification = Classification.INCONCLUSIVO
        score_confianca = 0.0
        findings = []
        resumo = ""

        class_match = re.search(
            r"\*\*Classificação:\*\*\s*(SUSPECTA|SUSPEITA|NÃO_SUSPEITA|INCONCLUSIVO)",
            content,
            re.IGNORECASE,
        )
        if class_match:
            cls_text = class_match.group(1).upper()
            if "SUSPECTA" in cls_text or "SUSPEITA" in cls_text:
                classification = Classification.SUSPEITA
            elif "NÃO_SUSPEITA" in cls_text or "NAO_SUSPEITA" in cls_text:
                classification = Classification.NAO_SUSPEITA
            else:
                classification = Classification.INCONCLUSIVO

        score_match = re.search(
            r"\*\*Score[^:]*:\*\*\s*(0\.\d+|1\.0|0|1)", content, re.IGNORECASE
        )
        if score_match:
            try:
                score_confianca = float(score_match.group(1))
            except ValueError:
                pass

        finding_blocks = re.findall(
            r"(?:^|\n)(?:[-*#]|\d+\.)\s*\*\*(?:Termo|Referência|Violação)[^:]*:\*\*\s*([^\n]+)",
            content,
            re.IGNORECASE,
        )
        if not finding_blocks:
            finding_blocks = re.findall(
                r"(?:^|\n)(?:[-*])\s*([^-\n]+?)(?:\n|$)", content
            )

        resumo_match = re.search(
            r"\*\*Resumo[^:]*:\*\*\s*([^\n]+)", content, re.IGNORECASE
        )
        if resumo_match:
            resumo = resumo_match.group(1).strip()
        else:
            resumo_match = re.search(
                r"(?:classificado como|devido a|from|due to)[^.]*\.?",
                content,
                re.IGNORECASE,
            )
            if resumo_match:
                resumo = resumo_match.group(0).strip()[:200]

        if len(content) > 50 and not resumo:
            resumo = content[:150].strip()

        return AnalysisResult(
            url="",
            titulo="",
            classificacao=classification,
            score_confianca=score_confianca,
            findings=findings,
            resumo=resumo,
        )


def save_result_json(result: AnalysisResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "url": result.url,
        "titulo": result.titulo,
        "classificacao": result.classificacao.value,
        "score_confianca": result.score_confianca,
        "findings": [asdict(f) for f in result.findings],
        "resumo": result.resumo,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_result_md(result: AnalysisResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    emoji = {
        Classification.SUSPEITA: "🔴",
        Classification.NAO_SUSPEITA: "🟢",
        Classification.INCONCLUSIVO: "⚪",
    }
    e = emoji.get(result.classificacao, "⚪")

    md = f"""# Análise: {result.titulo}

**URL:** {result.url}  
**Classificação:** {e} {result.classificacao.value} ({result.score_confianca:.0%})

## Findings

"""
    if not result.findings:
        md += "*Nenhuma violação encontrada.*\n"
    else:
        for f in result.findings:
            md += f"""### {f.modulo.upper()}: {f.termo_encontrado}
- **Trecho:** "{f.trecho_exato[:150]}..."
- **Violação:** {f.violacao}
- **Evidência:** {f.evidencia_ref}

"""

    md += f"""
## Resumo

{result.resumo}
"""
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    analyzer = CTAnalyzer()
    print(f"CT Analyzer initialized with provider: {analyzer.llm.provider}")
    print(f"Model: {analyzer.llm.model}")
