"""Wiki index generator - regenerates a navigable index from all markdown files."""

from __future__ import annotations

import datetime
from pathlib import Path

from kb_builder.storage import list_md_files, read_file_content


def _extract_title(content: str) -> str:
    """Extract the first H1 heading from markdown content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled"


def _extract_sections(content: str) -> list[str]:
    """Extract H2 headings from markdown content as section names."""
    sections: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            sections.append(stripped[3:].strip())
    return sections


def _word_count(content: str) -> int:
    """Count words in content."""
    return len(content.split())


def generate_wiki_index(kb_dir: Path) -> Path:
    """Regenerate the wiki index (WIKI.md) from all knowledge base markdown files.

    The index contains:
    - A table of contents with links to each topic file
    - Section listings for each file
    - Word count statistics
    - Last-updated timestamp
    """
    md_files = list_md_files(kb_dir)
    # Exclude WIKI.md itself from the listing
    md_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Knowledge Base Wiki",
        "",
        f"> Auto-generated on {now}",
        f"> Total topics: {len(md_files)}",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    total_words = 0

    for md_file in md_files:
        content = read_file_content(md_file)
        title = _extract_title(content)
        sections = _extract_sections(content)
        words = _word_count(content)
        total_words += words

        lines.append(f"### [{title}](./{md_file.name})")
        lines.append(f"*{words} words*")
        lines.append("")

        if sections:
            for section in sections:
                lines.append(f"- {section}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Statistics",
            "",
            f"- **Total topics**: {len(md_files)}",
            f"- **Total words**: {total_words}",
            f"- **Last updated**: {now}",
            "",
        ]
    )

    wiki_path = kb_dir / "WIKI.md"
    wiki_path.write_text("\n".join(lines), encoding="utf-8")
    return wiki_path
