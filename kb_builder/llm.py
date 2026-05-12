"""LLM integration for classifying user input and routing to markdown files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a knowledge base organizer. The user will give you a piece of text they typed.
Your job is to:
1. Determine the TOPIC/CATEGORY this text belongs to
   (e.g., "Python", "Docker", "Git", "Networking", "General").
2. Decide the markdown FILENAME where this should be stored
   (lowercase, hyphens, no spaces, e.g., "python.md", "docker-compose.md").
3. Produce a well-formatted MARKDOWN SNIPPET to append to that file. The snippet should:
   - Use appropriate headers (##, ###) if introducing a new sub-topic.
   - Use bullet points, code blocks, or tables as appropriate.
   - Be concise but preserve all information from the user's input.
   - NOT repeat the top-level heading (the file title is managed separately).

Respond with valid JSON only:
{
  "topic": "<topic name>",
  "filename": "<filename>.md",
  "markdown": "<formatted markdown snippet to append>"
}
"""


@dataclass
class Classification:
    topic: str
    filename: str
    markdown: str


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Set OPENAI_KEY or OPENAI_API_KEY environment variable."
        )
    return OpenAI(api_key=api_key)


def classify_input(client: OpenAI, user_text: str) -> Classification:
    """Send user input to the LLM and get back a classification with formatted markdown."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)

    return Classification(
        topic=data.get("topic", "General"),
        filename=data.get("filename", "general.md"),
        markdown=data.get("markdown", user_text),
    )
