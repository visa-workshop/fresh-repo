"""Ingest raw documents into the knowledge base via LLM compilation."""

from __future__ import annotations

from pathlib import Path

import litellm

from kb_builder.llm import get_model
from kb_builder.storage import append_to_file

INGEST_PROMPT = """\
You are a knowledge base compiler. You will receive the contents of a raw document.
Your job is to:
1. Summarize and organize the key information from the document.
2. Determine the TOPIC/CATEGORY this content belongs to.
3. Decide the markdown FILENAME where this should be stored
   (lowercase, hyphens, no spaces, e.g., "python.md", "machine-learning.md").
4. Produce a well-formatted MARKDOWN SNIPPET to append to that file. The snippet should:
   - Include a source reference (filename or URL).
   - Use appropriate headers (##, ###) for sub-topics.
   - Extract key facts, concepts, and relationships.
   - Use bullet points, code blocks, or tables as appropriate.
   - NOT repeat the top-level heading (the file title is managed separately).

Respond with valid JSON only:
{
  "topic": "<topic name>",
  "filename": "<filename>.md",
  "markdown": "<formatted markdown snippet to append>"
}
"""

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".py",
    ".js",
    ".ts",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".go",
    ".rs",
    ".rb",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
    ".html",
    ".css",
    ".xml",
    ".csv",
    ".log",
    ".rst",
    ".tex",
}


def _read_file(filepath: Path) -> str:
    """Read a file's content as text."""
    return filepath.read_text(encoding="utf-8", errors="replace")


def ingest_file(filepath: Path, kb_dir: Path, model: str | None = None) -> tuple[str, str, Path]:
    """Ingest a single file into the knowledge base.

    Returns (topic, filename, saved_path).
    """
    import json

    content = _read_file(filepath)
    source_info = f"Source: {filepath.name}"

    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": INGEST_PROMPT},
            {
                "role": "user",
                "content": f"{source_info}\n\n---\n\n{content[:8000]}",
            },
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    topic = data.get("topic", "General")
    filename = data.get("filename", "general.md")
    markdown = data.get("markdown", content[:500])

    saved_path = append_to_file(kb_dir, filename, topic, markdown)
    return topic, filename, saved_path


def ingest_directory(
    dirpath: Path,
    kb_dir: Path,
    model: str | None = None,
    recursive: bool = True,
) -> list[tuple[str, str, Path]]:
    """Ingest all supported files from a directory.

    Returns list of (topic, filename, saved_path) for each ingested file.
    """
    results: list[tuple[str, str, Path]] = []
    glob_pattern = "**/*" if recursive else "*"

    for filepath in sorted(dirpath.glob(glob_pattern)):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        # Skip hidden files and directories
        if any(part.startswith(".") for part in filepath.parts):
            continue

        result = ingest_file(filepath, kb_dir, model=model)
        results.append(result)

    return results
