"""LLM integration for classifying user input and routing to markdown files."""

from __future__ import annotations

import json
import os
import ssl
from dataclasses import dataclass

import httpx
import litellm

CLASSIFY_PROMPT = """\
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

INTENT_PROMPT = """\
You are an intent classifier for a knowledge base application.
The user types text into a terminal. Decide whether the user is:
- "store": providing information, facts, notes, or knowledge to save
- "query": asking a question or requesting information from the knowledge base

Respond with valid JSON only:
{
  "intent": "store" or "query"
}
"""

QUERY_PROMPT = """\
You are a helpful assistant that answers questions using ONLY the knowledge base \
content provided below. If the answer is not in the knowledge base, say so honestly. \
Do not make up information. Be concise and direct.

--- KNOWLEDGE BASE CONTENT ---
{kb_content}
--- END KNOWLEDGE BASE ---
"""


@dataclass
class Classification:
    topic: str
    filename: str
    markdown: str


def configure_litellm() -> None:
    """Configure litellm with API key, optional base URL, and optional CA bundle."""
    api_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Set OPENAI_KEY or OPENAI_API_KEY environment variable."
        )
    # litellm reads OPENAI_API_KEY by default; sync if only OPENAI_KEY is set
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_key

    # Custom base URL (e.g. corporate proxy, Azure, local LLM server)
    base_url = os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if base_url:
        litellm.api_base = base_url

    # Custom CA bundle for TLS verification
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca_bundle:
        ssl_ctx = ssl.create_default_context(cafile=ca_bundle)
        litellm.client_session = httpx.Client(verify=ssl_ctx)
        litellm.aclient_session = httpx.AsyncClient(verify=ssl_ctx)


DEFAULT_MODEL = "gpt-4o-mini"


def get_model() -> str:
    """Return the configured model name from env var or default."""
    return os.environ.get("LITELLM_MODEL", DEFAULT_MODEL)


def detect_intent(user_text: str, model: str | None = None) -> str:
    """Detect whether the user wants to store information or query the KB.

    Returns "store" or "query".
    """
    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    intent = data.get("intent", "store")
    return intent if intent in ("store", "query") else "store"


def classify_input(user_text: str, model: str | None = None) -> Classification:
    """Send user input to the LLM and get back a classification with formatted markdown."""
    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": CLASSIFY_PROMPT},
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


def answer_query(user_text: str, kb_content: str, model: str | None = None) -> str:
    """Answer a user question using the knowledge base content as context."""
    system_msg = QUERY_PROMPT.format(kb_content=kb_content)
    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content or "I couldn't generate an answer."
