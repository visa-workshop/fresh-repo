"""Task tracker - timestamped activity logging with weekly summaries."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import litellm

from kb_builder.llm import get_model

TASKS_FILE = "tasks.jsonl"

WEEKLY_PROMPT = """\
You are a professional work summary generator. You will receive a list of timestamped \
task entries from someone's work week. Generate a comprehensive weekly summary covering:

1. **Major Deliverables**: What was shipped, completed, or produced.
2. **Discussions & Meetings**: Key conversations, decisions made, alignment reached.
3. **Value Created**: Business impact, improvements, efficiencies gained.
4. **Issues Solved**: Bugs fixed, blockers removed, problems resolved.
5. **Team Contributions**: How this person helped teammates, unblocked others, \
mentored, or moved the team forward.
6. **Key Highlights**: Most impactful moments of the week.

Be specific, use the actual task descriptions, and organize by category. \
Use markdown formatting. Be professional but human. \
If there aren't enough entries for a category, note that briefly rather than making things up.
"""


def _tasks_path(kb_dir: Path) -> Path:
    """Return the path to the tasks JSONL file."""
    return kb_dir / TASKS_FILE


def log_task(kb_dir: Path, description: str) -> datetime:
    """Log a timestamped task entry. Returns the timestamp used."""
    now = datetime.now(timezone.utc)
    entry = {
        "timestamp": now.isoformat(),
        "description": description,
    }

    tasks_file = _tasks_path(kb_dir)
    with open(tasks_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return now


def load_tasks(
    kb_dir: Path,
    days: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Load task entries, optionally filtered by recent days or limited count."""
    tasks_file = _tasks_path(kb_dir)
    if not tasks_file.exists():
        return []

    entries: list[dict] = []
    with open(tasks_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            entries.append(entry)

    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        entries = [e for e in entries if datetime.fromisoformat(e["timestamp"]) >= cutoff]

    if limit is not None:
        entries = entries[-limit:]

    return entries


def generate_weekly_summary(kb_dir: Path, model: str | None = None) -> str:
    """Generate an AI-powered weekly summary from task entries."""
    entries = load_tasks(kb_dir, days=7)

    if not entries:
        return "No task entries found for the past week. Start logging with `:task <description>`."

    # Format entries for the LLM
    formatted_lines: list[str] = []
    for entry in entries:
        ts = datetime.fromisoformat(entry["timestamp"])
        day_name = ts.strftime("%A")
        time_str = ts.strftime("%Y-%m-%d %H:%M")
        formatted_lines.append(f"[{day_name} {time_str}] {entry['description']}")

    tasks_text = "\n".join(formatted_lines)

    date_range_start = datetime.fromisoformat(entries[0]["timestamp"]).strftime("%b %d")
    date_range_end = datetime.fromisoformat(entries[-1]["timestamp"]).strftime("%b %d, %Y")

    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": WEEKLY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Week of {date_range_start} - {date_range_end}\n"
                    f"Total entries: {len(entries)}\n\n"
                    f"--- TASK LOG ---\n{tasks_text}\n--- END LOG ---"
                ),
            },
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content or "Unable to generate summary."


def generate_daily_summary(kb_dir: Path, model: str | None = None) -> str:
    """Generate an AI-powered daily summary from today's task entries."""
    entries = load_tasks(kb_dir, days=1)

    if not entries:
        return "No task entries found for today. Start logging with `:task <description>`."

    formatted_lines: list[str] = []
    for entry in entries:
        ts = datetime.fromisoformat(entry["timestamp"])
        time_str = ts.strftime("%H:%M")
        formatted_lines.append(f"[{time_str}] {entry['description']}")

    tasks_text = "\n".join(formatted_lines)
    today_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    response = litellm.completion(
        model=model or get_model(),
        messages=[
            {"role": "system", "content": WEEKLY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Daily summary for {today_str}\n"
                    f"Total entries: {len(entries)}\n\n"
                    f"--- TASK LOG ---\n{tasks_text}\n--- END LOG ---"
                ),
            },
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content or "Unable to generate summary."
