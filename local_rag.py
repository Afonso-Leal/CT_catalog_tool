"""
RAG local (leve, sem embeddings) para base pequena.

Implementa:
- chunking simples da base (por headings Markdown)
- busca por similaridade via scoring token-based (estilo BM25 simplificado)
- seleção de trechos mais relevantes do conteúdo do site
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{2,}", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def _split_paragraphs(text: str) -> List[str]:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras


@dataclass(frozen=True)
class KBChunk:
    chunk_id: str
    title: str
    text: str


def load_kb_chunks_md(path: str | Path, max_chars: int = 200_000) -> List[KBChunk]:
    """
    Carrega um Markdown e chunk-a por headings (#, ##, ###...).
    """

    p = Path(path)
    raw = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
    lines = raw.splitlines()

    chunks: list[KBChunk] = []
    current_title = "INTRO"
    current_lines: list[str] = []
    section_idx = 0

    def flush():
        nonlocal section_idx, current_lines, current_title
        text = "\n".join(current_lines).strip()
        if text:
            section_idx += 1
            chunks.append(
                KBChunk(
                    chunk_id=f"kb_{section_idx:04d}",
                    title=current_title.strip()[:120],
                    text=text,
                )
            )
        current_lines = []

    for line in lines:
        if re.match(r"^\s{0,3}#{1,6}\s+\S", line):
            flush()
            current_title = line.lstrip("#").strip()
            continue
        current_lines.append(line)

    flush()
    return chunks


def bm25_like_scores(query_tokens: Sequence[str], docs_tokens: List[List[str]]) -> List[float]:
    """
    Scoring inspirado em BM25 (simplificado).
    Bom o suficiente para base pequena sem dependências.
    """

    if not query_tokens or not docs_tokens:
        return [0.0 for _ in docs_tokens]

    # DF
    df: dict[str, int] = {}
    for toks in docs_tokens:
        seen = set(toks)
        for t in seen:
            df[t] = df.get(t, 0) + 1

    N = len(docs_tokens)
    avgdl = sum(len(t) for t in docs_tokens) / max(N, 1)
    k1 = 1.2
    b = 0.75

    # TF per doc
    scores: list[float] = []
    qset = list(dict.fromkeys(query_tokens))  # stable unique

    for toks in docs_tokens:
        dl = len(toks)
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1

        s = 0.0
        for term in qset:
            if term not in tf:
                continue
            n_qi = df.get(term, 0)
            # idf suavizado
            idf = math.log(1.0 + (N - n_qi + 0.5) / (n_qi + 0.5))
            f = tf[term]
            denom = f + k1 * (1.0 - b + b * (dl / max(avgdl, 1.0)))
            s += idf * (f * (k1 + 1.0)) / max(denom, 1e-9)
        scores.append(s)

    return scores


def retrieve_kb(
    kb_chunks: Sequence[KBChunk],
    query_text: str,
    top_k: int = 5,
    max_chunk_chars: int = 1200,
) -> List[KBChunk]:
    """
    Retorna top-k chunks de KB mais similares ao query_text.
    """

    q_tokens = _tokenize(query_text)
    docs_tokens = [_tokenize(c.text) for c in kb_chunks]
    scores = bm25_like_scores(q_tokens, docs_tokens)

    ranked = sorted(
        zip(kb_chunks, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    out: list[KBChunk] = []
    for c, s in ranked[: max(top_k, 0)]:
        if s <= 0:
            continue
        out.append(
            KBChunk(
                chunk_id=c.chunk_id,
                title=c.title,
                text=c.text[:max_chunk_chars].strip(),
            )
        )
    return out


def extract_focus_terms(*lists: Iterable[str], limit: int = 60) -> List[str]:
    """
    Extrai termos "âncora" a partir de listas textuais (ex.: regras/características).
    """

    terms: list[str] = []
    for lst in lists:
        for s in lst:
            for t in _tokenize(str(s)):
                # corta palavras muito genéricas
                if t in {"para", "com", "sem", "mais", "menos", "deve", "devem", "não", "nao"}:
                    continue
                terms.append(t)

    # unique mantendo ordem
    uniq: list[str] = []
    seen = set()
    for t in terms:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
        if len(uniq) >= limit:
            break
    return uniq


def select_relevant_text(
    site_text: str,
    focus_terms: Sequence[str],
    max_chars: int = 15000,
    max_paras: int = 80,
) -> str:
    """
    Seleciona os parágrafos mais relevantes do site para caber em max_chars.
    Heurística: pontuar parágrafos por ocorrência de termos foco.
    """

    paras = _split_paragraphs(site_text)[: max_paras * 5]
    if not paras:
        return ""

    focus = [t.lower() for t in focus_terms if t]
    if not focus:
        return "\n\n".join(paras)[:max_chars]

    scored: list[tuple[float, int, str]] = []
    for idx, p in enumerate(paras):
        toks = _tokenize(p)
        if not toks:
            continue
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in focus:
            score += min(tf.get(t, 0), 3)  # cap
        # bônus leve pra parágrafos com números (tempo, dias, valores) e palavras-chave fortes
        if re.search(r"\b\d{1,4}\b", p):
            score += 0.5
        if re.search(r"\b(laborterapia|volunt[aá]ri[ao]|involunt[aá]ri[ao]|contrato|disciplina|relig|deus|fé|licen[çc]a|alvar[aá])\b", p, re.I):
            score += 1.0
        scored.append((score, idx, p))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    chosen: list[str] = []
    used = set()
    total = 0
    for score, idx, p in scored:
        if score <= 0:
            continue
        if idx in used:
            continue
        p2 = p.strip()
        if not p2:
            continue
        if total + len(p2) + 2 > max_chars:
            continue
        chosen.append(p2)
        used.add(idx)
        total += len(p2) + 2
        if len(chosen) >= max_paras:
            break

    if not chosen:
        return "\n\n".join(paras)[:max_chars]

    # ordenar por posição original para manter legibilidade
    chosen_sorted = [p for _, i, p in sorted((i, i, paras[i]) for i in used)]
    return "\n\n".join(chosen_sorted)[:max_chars]

