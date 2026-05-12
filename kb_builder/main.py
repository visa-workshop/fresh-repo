"""Main entry point - terminal input loop with periodic wiki regeneration."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from kb_builder.clip import clip_url
from kb_builder.ingest import ingest_directory, ingest_file
from kb_builder.lint_kb import lint_knowledge_base
from kb_builder.llm import (
    DEFAULT_MODEL,
    Classification,
    answer_query,
    classify_input,
    configure_litellm,
    detect_intent,
)
from kb_builder.search import search_kb
from kb_builder.storage import (
    append_to_file,
    get_file_stats,
    get_kb_dir,
    list_md_files,
    read_file_content,
)
from kb_builder.tasks import (
    generate_daily_summary,
    generate_weekly_summary,
    load_tasks,
    log_task,
)
from kb_builder.webui import start_web_ui
from kb_builder.wiki import generate_wiki_index

console = Console()

DEFAULT_WIKI_INTERVAL = 60

# Stores the last query answer so it can be filed back with :save
_last_query_answer: str | None = None


def _print_welcome(kb_dir: Path) -> None:
    console.print(
        Panel(
            "[bold cyan]Terminal Knowledge Base Builder[/bold cyan]\n\n"
            "Type anything and it will be classified by an LLM and saved\n"
            "to the appropriate markdown file in your knowledge base.\n"
            "Ask questions and it will answer from your stored knowledge.\n\n"
            f"[dim]Knowledge base directory: {kb_dir}[/dim]\n\n"
            "[bold]Commands:[/bold]\n"
            "  [green]:wiki[/green]           - Regenerate the wiki index now\n"
            "  [green]:stats[/green]          - Show knowledge base statistics\n"
            "  [green]:show[/green]           - Display the current wiki index\n"
            "  [green]:ingest <path>[/green]  - Ingest a file or directory into KB\n"
            "  [green]:clip <url>[/green]     - Clip a web article into KB\n"
            "  [green]:search <query>[/green] - Search across KB content\n"
            "  [green]:lint[/green]           - Run LLM health checks on KB\n"
            "  [green]:save[/green]           - Save last query answer to KB\n"
            "  [green]:task <text>[/green]    - Log a timestamped task/activity\n"
            "  [green]:tasks[/green]          - Show recent task entries\n"
            "  [green]:daily[/green]          - Generate today's summary\n"
            "  [green]:weekly[/green]         - Generate weekly summary\n"
            "  [green]:web[/green]            - Start web UI viewer\n"
            "  [green]:quit[/green]           - Exit the application\n"
            "  [green]:help[/green]           - Show this help message",
            title="KB Builder",
            border_style="cyan",
        )
    )


def _print_classification(result: Classification, filepath: Path) -> None:
    console.print(f"\n  [bold green]Topic:[/bold green] {result.topic}")
    console.print(f"  [bold green]File:[/bold green]  {filepath.name}")
    console.print(f"  [dim]Saved to {filepath}[/dim]")
    console.print()


def _show_stats(kb_dir: Path) -> None:
    stats = get_file_stats(kb_dir)
    if not stats:
        console.print("[yellow]No knowledge base files yet. Start typing![/yellow]")
        return
    console.print("\n[bold]Knowledge Base Statistics:[/bold]")
    for name, line_count in stats.items():
        console.print(f"  {name}: {line_count} lines")
    console.print()


def _show_wiki(kb_dir: Path) -> None:
    wiki_path = kb_dir / "WIKI.md"
    if not wiki_path.exists():
        console.print("[yellow]Wiki not generated yet. Type ':wiki' to generate.[/yellow]")
        return
    content = wiki_path.read_text(encoding="utf-8")
    console.print(Markdown(content))


def _load_kb_content(kb_dir: Path) -> str:
    """Load all knowledge base markdown content into a single string."""
    md_files = list_md_files(kb_dir)
    md_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]
    if not md_files:
        return ""
    parts: list[str] = []
    for f in md_files:
        parts.append(f"=== {f.name} ===\n{read_file_content(f)}")
    return "\n\n".join(parts)


def _handle_store(user_input: str, kb_dir: Path, model: str | None) -> None:
    """Classify user input and store it in the appropriate markdown file."""
    with console.status("[bold yellow]Classifying...[/bold yellow]"):
        result = classify_input(user_input, model=model)
    filepath = append_to_file(kb_dir, result.filename, result.topic, result.markdown)
    _print_classification(result, filepath)


def _handle_query(user_input: str, kb_dir: Path, model: str | None) -> None:
    """Answer a user question from the knowledge base content."""
    global _last_query_answer
    kb_content = _load_kb_content(kb_dir)
    if not kb_content:
        console.print(
            "\n[yellow]Knowledge base is empty. "
            "Add some knowledge first, then ask questions![/yellow]\n"
        )
        return
    with console.status("[bold yellow]Searching knowledge base...[/bold yellow]"):
        response = answer_query(user_input, kb_content, model=model)
    _last_query_answer = response
    console.print("\n[bold blue]Answer:[/bold blue]")
    console.print(Markdown(response))
    console.print("[dim]Use :save to file this answer into the KB[/dim]")
    console.print()


def _handle_ingest(arg: str, kb_dir: Path, model: str | None) -> None:
    """Ingest a file or directory into the knowledge base."""
    path = Path(arg).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Path not found: {path}[/red]")
        return

    if path.is_file():
        with console.status(f"[bold yellow]Ingesting {path.name}...[/bold yellow]"):
            topic, filename, saved = ingest_file(path, kb_dir, model=model)
        console.print(f"\n  [bold green]Ingested:[/bold green] {path.name}")
        console.print(f"  [bold green]Topic:[/bold green]    {topic}")
        console.print(f"  [bold green]File:[/bold green]     {filename}")
        console.print(f"  [dim]Saved to {saved}[/dim]\n")
    elif path.is_dir():
        console.print(f"[cyan]Ingesting directory: {path}[/cyan]")
        results = ingest_directory(path, kb_dir, model=model)
        if not results:
            console.print("[yellow]No supported files found.[/yellow]")
        else:
            for topic, filename, saved in results:
                console.print(f"  [green]{filename}[/green] ({topic}) -> {saved.name}")
            console.print(f"\n[bold green]Ingested {len(results)} files.[/bold green]\n")


def _handle_clip(url: str, kb_dir: Path, model: str | None) -> None:
    """Clip a web article and ingest it."""
    with console.status(f"[bold yellow]Clipping {url}...[/bold yellow]"):
        topic, filename, saved = clip_url(url, kb_dir, model=model)
    console.print(f"\n  [bold green]Clipped:[/bold green] {url}")
    console.print(f"  [bold green]Topic:[/bold green]   {topic}")
    console.print(f"  [bold green]File:[/bold green]    {filename}")
    console.print(f"  [dim]Saved to {saved}[/dim]\n")


def _handle_search(query: str, kb_dir: Path) -> None:
    """Search across KB content."""
    results = search_kb(kb_dir, query)
    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        return
    console.print(f"\n[bold]Found {len(results)} match(es) for '{query}':[/bold]\n")
    for r in results[:20]:
        console.print(f"  [bold cyan]{r.filename}[/bold cyan] (line {r.line_number}):")
        for ctx_line in r.context.splitlines():
            console.print(f"    {ctx_line}")
        console.print()


def _handle_lint(kb_dir: Path, model: str | None) -> None:
    """Run LLM health checks on the KB."""
    with console.status("[bold yellow]Running KB health checks...[/bold yellow]"):
        report = lint_knowledge_base(kb_dir, model=model)

    score = report.get("score", 0)
    color = "green" if score >= 7 else "yellow" if score >= 4 else "red"
    console.print(f"\n[bold {color}]Health Score: {score}/10[/bold {color}]")
    console.print(f"[dim]{report.get('summary', '')}[/dim]\n")

    sections = [
        ("Inconsistencies", "inconsistencies", "red"),
        ("Missing Data", "missing_data", "yellow"),
        ("Connection Suggestions", "connections", "cyan"),
        ("Integrity Issues", "integrity_issues", "red"),
        ("Enhancement Ideas", "enhancements", "green"),
    ]
    for title, key, clr in sections:
        items = report.get(key, [])
        if items:
            console.print(f"[bold {clr}]{title}:[/bold {clr}]")
            for item in items:
                console.print(f"  - {item}")
            console.print()


def _handle_save(kb_dir: Path, model: str | None) -> None:
    """Save the last query answer back into the KB."""
    global _last_query_answer
    if not _last_query_answer:
        console.print("[yellow]No recent query answer to save.[/yellow]")
        return
    with console.status("[bold yellow]Filing answer into KB...[/bold yellow]"):
        result = classify_input(_last_query_answer, model=model)
    filepath = append_to_file(kb_dir, result.filename, result.topic, result.markdown)
    console.print(f"\n  [bold green]Answer filed:[/bold green] {result.topic}")
    console.print(f"  [bold green]File:[/bold green]        {filepath.name}")
    console.print(f"  [dim]Saved to {filepath}[/dim]\n")
    _last_query_answer = None


def _handle_task(description: str, kb_dir: Path) -> None:
    """Log a timestamped task entry."""
    from datetime import timezone

    ts = log_task(kb_dir, description)
    local_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    console.print(f"\n  [bold green]Task logged:[/bold green] {description}")
    console.print(f"  [dim]{local_str}[/dim]\n")


def _handle_tasks(kb_dir: Path) -> None:
    """Show recent task entries."""
    entries = load_tasks(kb_dir, limit=20)
    if not entries:
        console.print("[yellow]No task entries yet. Use :task <description> to log.[/yellow]")
        return
    console.print("\n[bold]Recent Task Entries:[/bold]\n")
    from datetime import datetime

    for entry in entries:
        ts = datetime.fromisoformat(entry["timestamp"])
        day_name = ts.strftime("%a")
        time_str = ts.strftime("%Y-%m-%d %H:%M")
        console.print(f"  [cyan]{day_name} {time_str}[/cyan]  {entry['description']}")
    console.print()


def _handle_weekly(kb_dir: Path, model: str | None) -> None:
    """Generate weekly summary."""
    with console.status("[bold yellow]Generating weekly summary...[/bold yellow]"):
        summary = generate_weekly_summary(kb_dir, model=model)
    console.print("\n[bold blue]Weekly Summary:[/bold blue]")
    console.print(Markdown(summary))
    console.print()


def _handle_daily(kb_dir: Path, model: str | None) -> None:
    """Generate daily summary."""
    with console.status("[bold yellow]Generating daily summary...[/bold yellow]"):
        summary = generate_daily_summary(kb_dir, model=model)
    console.print("\n[bold blue]Today's Summary:[/bold blue]")
    console.print(Markdown(summary))
    console.print()


def _wiki_regen_loop(kb_dir: Path, interval: int, stop_event: threading.Event) -> None:
    """Background thread that periodically regenerates the wiki index."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        try:
            md_files = list(kb_dir.glob("*.md"))
            topic_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]
            if topic_files:
                generate_wiki_index(kb_dir)
                console.print(
                    "\n[dim cyan]Wiki index auto-regenerated.[/dim cyan]",
                    highlight=False,
                )
        except Exception as e:
            console.print(f"\n[dim red]Wiki regen error: {e}[/dim red]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Terminal Knowledge Base Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=None,
        help="Knowledge base directory (default: ./knowledge_base)",
    )
    parser.add_argument(
        "--wiki-interval",
        type=int,
        default=DEFAULT_WIKI_INTERVAL,
        help=f"Wiki auto-regeneration interval in seconds (default: {DEFAULT_WIKI_INTERVAL})",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=None,
        help=f"LLM model name (default: {DEFAULT_MODEL}, or set LITELLM_MODEL env var)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the web UI viewer on launch",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8899,
        help="Port for the web UI viewer (default: 8899)",
    )
    args = parser.parse_args()

    kb_dir = get_kb_dir(args.directory)
    _print_welcome(kb_dir)

    # Configure litellm (API key, base URL, CA bundle)
    try:
        configure_litellm()
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    # Optionally start web UI on launch
    if args.web:
        _, port = start_web_ui(kb_dir, args.web_port)
        console.print(f"[bold green]Web UI started at http://localhost:{port}[/bold green]\n")

    # Start background wiki regeneration thread
    stop_event = threading.Event()
    wiki_thread = threading.Thread(
        target=_wiki_regen_loop,
        args=(kb_dir, args.wiki_interval, stop_event),
        daemon=True,
    )
    wiki_thread.start()

    def _handle_sigint(signum: int, frame: object) -> None:
        console.print("\n[yellow]Shutting down...[/yellow]")
        stop_event.set()
        try:
            generate_wiki_index(kb_dir)
            console.print("[green]Final wiki index generated.[/green]")
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    # Main input loop
    while True:
        try:
            user_input = console.input("[bold cyan]kb>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye![/yellow]")
            stop_event.set()
            break

        if not user_input:
            continue

        lower = user_input.lower()

        # Handle commands
        if lower == ":quit":
            console.print("[yellow]Shutting down...[/yellow]")
            stop_event.set()
            try:
                generate_wiki_index(kb_dir)
                console.print("[green]Final wiki index generated.[/green]")
            except Exception:
                pass
            break

        if lower == ":wiki":
            try:
                wiki_path = generate_wiki_index(kb_dir)
                console.print(f"[green]Wiki index regenerated: {wiki_path}[/green]")
            except Exception as e:
                console.print(f"[red]Error generating wiki: {e}[/red]")
            continue

        if lower == ":stats":
            _show_stats(kb_dir)
            continue

        if lower == ":show":
            _show_wiki(kb_dir)
            continue

        if lower == ":help":
            _print_welcome(kb_dir)
            continue

        if lower.startswith(":ingest "):
            arg = user_input[8:].strip()
            if not arg:
                console.print("[red]Usage: :ingest <file_or_directory>[/red]")
            else:
                try:
                    _handle_ingest(arg, kb_dir, args.model)
                except Exception as e:
                    console.print(f"[bold red]Ingest error:[/bold red] {e}")
            continue

        if lower.startswith(":clip "):
            url = user_input[6:].strip()
            if not url:
                console.print("[red]Usage: :clip <url>[/red]")
            else:
                try:
                    _handle_clip(url, kb_dir, args.model)
                except Exception as e:
                    console.print(f"[bold red]Clip error:[/bold red] {e}")
            continue

        if lower.startswith(":search "):
            query = user_input[8:].strip()
            if not query:
                console.print("[red]Usage: :search <query>[/red]")
            else:
                _handle_search(query, kb_dir)
            continue

        if lower == ":lint":
            try:
                _handle_lint(kb_dir, args.model)
            except Exception as e:
                console.print(f"[bold red]Lint error:[/bold red] {e}")
            continue

        if lower == ":save":
            try:
                _handle_save(kb_dir, args.model)
            except Exception as e:
                console.print(f"[bold red]Save error:[/bold red] {e}")
            continue

        if lower.startswith(":task "):
            desc = user_input[6:].strip()
            if not desc:
                console.print("[red]Usage: :task <description>[/red]")
            else:
                try:
                    _handle_task(desc, kb_dir)
                except Exception as e:
                    console.print(f"[bold red]Task error:[/bold red] {e}")
            continue

        if lower == ":tasks":
            _handle_tasks(kb_dir)
            continue

        if lower == ":daily":
            try:
                _handle_daily(kb_dir, args.model)
            except Exception as e:
                console.print(f"[bold red]Daily summary error:[/bold red] {e}")
            continue

        if lower == ":weekly":
            try:
                _handle_weekly(kb_dir, args.model)
            except Exception as e:
                console.print(f"[bold red]Weekly summary error:[/bold red] {e}")
            continue

        if lower == ":web":
            try:
                _, port = start_web_ui(kb_dir, args.web_port)
                console.print(f"[bold green]Web UI started at http://localhost:{port}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Web UI error:[/bold red] {e}")
            continue

        # Detect intent: store knowledge or query the KB
        try:
            with console.status("[bold yellow]Thinking...[/bold yellow]"):
                intent = detect_intent(user_input, model=args.model)

            if intent == "query":
                _handle_query(user_input, kb_dir, args.model)
            else:
                _handle_store(user_input, kb_dir, args.model)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[dim]Please try again.[/dim]")

    # Clean up
    stop_event.set()
    wiki_thread.join(timeout=2)


if __name__ == "__main__":
    main()
