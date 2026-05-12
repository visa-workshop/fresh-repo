"""LLM-powered health checks and linting for the knowledge base."""

from __future__ import annotations

import json
from pathlib import Path

import litellm

from kb_builder.llm import get_model
from kb_builder.storage import list_md_files, read_file_content

LINT_PROMPT = """\
You are a knowledge base quality auditor. You will receive the full content of a \
markdown knowledge base. Analyze it and produce a health report covering:

1. **Inconsistencies**: Contradictory or conflicting information across articles.
2. **Missing Data**: Topics mentioned but not fully explained, gaps in coverage.
3. **Connection Suggestions**: Related topics that could be linked or merged, \
potential new articles that would bridge existing content.
4. **Data Integrity**: Formatting issues, broken references, orphaned content.
5. **Enhancement Ideas**: Suggestions for deeper coverage, questions worth exploring.

Respond with valid JSON only:
{
  "score": <1-10 overall health score>,
  "summary": "<brief overall assessment>",
  "inconsistencies": ["<issue1>", "<issue2>", ...],
  "missing_data": ["<gap1>", "<gap2>", ...],
  "connections": ["<suggestion1>", "<suggestion2>", ...],
  "integrity_issues": ["<issue1>", "<issue2>", ...],
  "enhancements": ["<idea1>", "<idea2>", ...]
}
"""


def lint_knowledge_base(kb_dir: Path, model: str | None = None) -> dict:
    """Run LLM health checks on the entire knowledge base.

    Returns a structured report dict.
    """
    md_files = list_md_files(kb_dir)
    md_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]

    if not md_files:
        return {
            "score": 0,
            "summary": "Knowledge base is empty.",
            "inconsistencies": [],
            "missing_data": [],
            "connections": [],
            "integrity_issues": [],
            "enhancements": ["Start adding knowledge to your base!"],
        }

    # Build full KB content
    parts: list[str] = []
    for f in md_files:
        parts.append(f"=== {f.name} ===\n{read_file_content(f)}")
    kb_content = "\n\n".join(parts)

    # Truncate if too long
    truncated = kb_content[:12000]

    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": LINT_PROMPT},
            {"role": "user", "content": truncated},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)
