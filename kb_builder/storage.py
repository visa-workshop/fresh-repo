"""Markdown file storage management for the knowledge base."""

from __future__ import annotations

from pathlib import Path


def get_kb_dir(base_dir: str | None = None) -> Path:
    """Return the knowledge base directory, creating it if needed."""
    if base_dir:
        kb_dir = Path(base_dir)
    else:
        kb_dir = Path.cwd() / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir


def append_to_file(kb_dir: Path, filename: str, topic: str, markdown_snippet: str) -> Path:
    """Append a markdown snippet to the appropriate file.

    Creates the file with a title header if it doesn't exist yet.
    """
    filepath = kb_dir / filename

    if not filepath.exists():
        filepath.write_text(f"# {topic}\n\n", encoding="utf-8")

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(markdown_snippet.rstrip("\n") + "\n\n")

    return filepath


def list_md_files(kb_dir: Path) -> list[Path]:
    """List all markdown files in the knowledge base directory."""
    return sorted(kb_dir.glob("*.md"))


def read_file_content(filepath: Path) -> str:
    """Read and return the content of a markdown file."""
    return filepath.read_text(encoding="utf-8")


def get_file_stats(kb_dir: Path) -> dict[str, int]:
    """Return a mapping of filename -> line count for all md files."""
    stats: dict[str, int] = {}
    for f in list_md_files(kb_dir):
        content = f.read_text(encoding="utf-8")
        stats[f.name] = len(content.splitlines())
    return stats
