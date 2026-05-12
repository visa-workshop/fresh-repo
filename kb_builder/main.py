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

from kb_builder.llm import Classification, classify_input, get_client
from kb_builder.storage import append_to_file, get_file_stats, get_kb_dir
from kb_builder.wiki import generate_wiki_index

console = Console()

# How often (in seconds) the wiki index is auto-regenerated
DEFAULT_WIKI_INTERVAL = 60


def _print_welcome(kb_dir: Path) -> None:
    console.print(
        Panel(
            "[bold cyan]Terminal Knowledge Base Builder[/bold cyan]\n\n"
            "Type anything and it will be classified by an LLM and saved\n"
            "to the appropriate markdown file in your knowledge base.\n\n"
            f"[dim]Knowledge base directory: {kb_dir}[/dim]\n\n"
            "[bold]Commands:[/bold]\n"
            "  [green]:wiki[/green]    - Regenerate the wiki index now\n"
            "  [green]:stats[/green]   - Show knowledge base statistics\n"
            "  [green]:show[/green]    - Show the current wiki index\n"
            "  [green]:quit[/green]    - Exit the application\n"
            "  [green]:help[/green]    - Show this help message",
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


def _wiki_regen_loop(kb_dir: Path, interval: int, stop_event: threading.Event) -> None:
    """Background thread that periodically regenerates the wiki index."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        try:
            md_files = list(kb_dir.glob("*.md"))
            # Only regenerate if there are topic files (excluding WIKI.md)
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
    args = parser.parse_args()

    kb_dir = get_kb_dir(args.directory)
    _print_welcome(kb_dir)

    # Initialize OpenAI client
    try:
        client = get_client()
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

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
        # Final wiki regeneration
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

        # Handle commands
        if user_input.lower() == ":quit":
            console.print("[yellow]Shutting down...[/yellow]")
            stop_event.set()
            try:
                generate_wiki_index(kb_dir)
                console.print("[green]Final wiki index generated.[/green]")
            except Exception:
                pass
            break

        if user_input.lower() == ":wiki":
            try:
                wiki_path = generate_wiki_index(kb_dir)
                console.print(f"[green]Wiki index regenerated: {wiki_path}[/green]")
            except Exception as e:
                console.print(f"[red]Error generating wiki: {e}[/red]")
            continue

        if user_input.lower() == ":stats":
            _show_stats(kb_dir)
            continue

        if user_input.lower() == ":show":
            _show_wiki(kb_dir)
            continue

        if user_input.lower() == ":help":
            _print_welcome(kb_dir)
            continue

        # Classify and store input via LLM
        try:
            with console.status("[bold yellow]Classifying...[/bold yellow]"):
                result = classify_input(client, user_input)

            filepath = append_to_file(kb_dir, result.filename, result.topic, result.markdown)
            _print_classification(result, filepath)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[dim]Your input was not saved. Please try again.[/dim]")

    # Clean up
    stop_event.set()
    wiki_thread.join(timeout=2)


if __name__ == "__main__":
    main()
