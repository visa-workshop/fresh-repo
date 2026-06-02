"""Search across knowledge base content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kb_builder.storage import list_md_files, read_file_content


@dataclass
class SearchResult:
    filename: str
    line_number: int
    line: str
    context: str


def search_kb(kb_dir: Path, query: str, context_lines: int = 2) -> list[SearchResult]:
    """Search all KB markdown files for a query string (case-insensitive).

    Returns matching lines with surrounding context.
    """
    results: list[SearchResult] = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    md_files = list_md_files(kb_dir)
    md_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]

    for filepath in md_files:
        content = read_file_content(filepath)
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = "\n".join(lines[start:end])
                results.append(
                    SearchResult(
                        filename=filepath.name,
                        line_number=i + 1,
                        line=line.strip(),
                        context=context,
                    )
                )

    return results
