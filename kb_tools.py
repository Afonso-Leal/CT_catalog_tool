"""
Ferramentas para navegação da base de conhecimento (KB) via CLI/chat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


DEFAULT_KB_PATH = Path("DATABASE_LEGISLACAO_COMUNIDADES_TERAPÊUTICAS_BRASIL.md")


@dataclass(frozen=True)
class KBHeading:
    level: int
    title: str
    line: int


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def list_kb_headings(kb_path: str | Path = DEFAULT_KB_PATH, max_items: int = 200) -> list[dict]:
    """
    Lista headings do Markdown com nível e linha.
    """

    p = Path(kb_path)
    text = _read_text(p)
    headings: List[KBHeading] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if not m:
            continue
        headings.append(KBHeading(level=len(m.group(1)), title=m.group(2).strip(), line=idx))
        if len(headings) >= max_items:
            break
    return [{"level": h.level, "title": h.title, "line": h.line} for h in headings]


def search_kb(
    query: str,
    kb_path: str | Path = DEFAULT_KB_PATH,
    max_hits: int = 20,
    context_lines: int = 2,
) -> list[dict]:
    """
    Busca literal simples na KB e retorna hits com contexto.
    """

    q = (query or "").strip()
    if not q:
        return []

    p = Path(kb_path)
    lines = _read_text(p).splitlines()
    hits: list[dict] = []
    q_low = q.lower()

    for i, line in enumerate(lines):
        if q_low not in line.lower():
            continue
        start = max(0, i - context_lines)
        end = min(len(lines), i + context_lines + 1)
        snippet = "\n".join(lines[start:end]).strip()
        hits.append({"line": i + 1, "snippet": snippet})
        if len(hits) >= max_hits:
            break

    return hits


def get_kb_section(
    title_contains: str,
    kb_path: str | Path = DEFAULT_KB_PATH,
    max_chars: int = 4000,
) -> dict:
    """
    Retorna a seção cujo heading contém `title_contains` (case-insensitive).
    """

    needle = (title_contains or "").strip().lower()
    if not needle:
        return {"error": "title_contains vazio"}

    p = Path(kb_path)
    text = _read_text(p)
    lines = text.splitlines()

    # acha heading
    start_idx = None
    start_level = None
    start_title = None
    for i, line in enumerate(lines):
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if not m:
            continue
        title = m.group(2).strip()
        if needle in title.lower():
            start_idx = i
            start_level = len(m.group(1))
            start_title = title
            break

    if start_idx is None:
        return {"error": f"Seção não encontrada contendo: {title_contains}"}

    # vai até próximo heading de nível <= atual
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", lines[j])
        if not m:
            continue
        if len(m.group(1)) <= (start_level or 6):
            end_idx = j
            break

    section_text = "\n".join(lines[start_idx:end_idx]).strip()
    return {
        "title": start_title,
        "start_line": start_idx + 1,
        "text": section_text[:max_chars],
        "truncated": len(section_text) > max_chars,
    }

