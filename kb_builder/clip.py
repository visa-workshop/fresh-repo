"""Web clipping - fetch web articles, convert to markdown, and ingest into KB."""

from __future__ import annotations

import json
from pathlib import Path

import html2text
import httpx
import litellm

from kb_builder.llm import get_model
from kb_builder.storage import append_to_file

CLIP_PROMPT = """\
You are a knowledge base compiler. You will receive the markdown-converted content \
of a web article. Your job is to:
1. Extract and organize the key information from the article.
2. Determine the TOPIC/CATEGORY this content belongs to.
3. Decide the markdown FILENAME where this should be stored
   (lowercase, hyphens, no spaces, e.g., "python.md", "machine-learning.md").
4. Produce a well-formatted MARKDOWN SNIPPET to append to that file. The snippet should:
   - Include the source URL as a reference.
   - Summarize the key points, concepts, and facts.
   - Use appropriate headers (##, ###) for sub-topics.
   - Use bullet points, code blocks, or tables as appropriate.
   - NOT repeat the top-level heading (the file title is managed separately).

Respond with valid JSON only:
{
  "topic": "<topic name>",
  "filename": "<filename>.md",
  "markdown": "<formatted markdown snippet to append>"
}
"""


def _fetch_and_convert(url: str) -> str:
    """Fetch a web page and convert to markdown."""
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(resp.text)


def clip_url(url: str, kb_dir: Path, model: str | None = None) -> tuple[str, str, Path]:
    """Clip a web article and ingest it into the knowledge base.

    Returns (topic, filename, saved_path).
    """
    md_content = _fetch_and_convert(url)

    # Truncate to avoid token limits
    truncated = md_content[:8000]

    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": CLIP_PROMPT},
            {
                "role": "user",
                "content": f"Source URL: {url}\n\n---\n\n{truncated}",
            },
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    topic = data.get("topic", "General")
    filename = data.get("filename", "general.md")
    markdown = data.get("markdown", truncated[:500])

    saved_path = append_to_file(kb_dir, filename, topic, markdown)
    return topic, filename, saved_path
