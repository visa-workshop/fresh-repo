"""Built-in web UI viewer for the knowledge base (replaces Obsidian)."""

from __future__ import annotations

import http.server
import re
import threading
from pathlib import Path

from kb_builder.storage import list_md_files, read_file_content

CSS = """\
:root { --bg: #1e1e2e; --fg: #cdd6f4; --accent: #89b4fa; --surface: #313244;
        --border: #45475a; --green: #a6e3a1; --yellow: #f9e2af; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--fg); line-height: 1.6; }
.container { display: flex; min-height: 100vh; }
.sidebar { width: 260px; background: var(--surface); padding: 1rem;
           border-right: 1px solid var(--border); position: fixed;
           height: 100vh; overflow-y: auto; }
.sidebar h2 { color: var(--accent); margin-bottom: 1rem; font-size: 1.1rem; }
.sidebar a { display: block; color: var(--fg); text-decoration: none;
             padding: 0.4rem 0.6rem; border-radius: 4px; margin-bottom: 2px; }
.sidebar a:hover, .sidebar a.active { background: var(--border); color: var(--accent); }
.sidebar .stats { margin-top: 1rem; padding-top: 1rem;
                  border-top: 1px solid var(--border); font-size: 0.85rem;
                  color: var(--yellow); }
.main { margin-left: 260px; padding: 2rem 3rem; max-width: 900px; flex: 1; }
h1 { color: var(--accent); margin-bottom: 1rem; border-bottom: 1px solid var(--border);
     padding-bottom: 0.5rem; }
h2 { color: var(--green); margin-top: 1.5rem; margin-bottom: 0.5rem; }
h3 { color: var(--yellow); margin-top: 1rem; margin-bottom: 0.5rem; }
p, li { margin-bottom: 0.5rem; }
code { background: var(--surface); padding: 0.15rem 0.4rem; border-radius: 3px;
       font-family: 'Fira Code', monospace; font-size: 0.9em; }
pre { background: var(--surface); padding: 1rem; border-radius: 6px;
      overflow-x: auto; margin: 1rem 0; border: 1px solid var(--border); }
pre code { background: none; padding: 0; }
a { color: var(--accent); }
ul, ol { padding-left: 1.5rem; }
table { border-collapse: collapse; margin: 1rem 0; width: 100%; }
th, td { border: 1px solid var(--border); padding: 0.5rem; text-align: left; }
th { background: var(--surface); }
.search-box { width: 100%; padding: 0.5rem; background: var(--bg);
              color: var(--fg); border: 1px solid var(--border);
              border-radius: 4px; margin-bottom: 1rem; }
"""


def _md_to_html(md: str) -> str:
    """Minimal markdown-to-HTML converter."""
    lines = md.split("\n")
    html_parts: list[str] = []
    in_code_block = False
    in_list = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                html_parts.append("</code></pre>")
                in_code_block = False
            else:
                html_parts.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
            continue

        # Headers
        if stripped.startswith("### "):
            html_parts.append(f"<h3>{_inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{_inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html_parts.append(f"<h1>{_inline(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline(stripped[2:])}</li>")
        elif stripped.startswith("> "):
            html_parts.append(
                f"<blockquote style='border-left:3px solid var(--accent);"
                f"padding-left:1rem;color:var(--yellow)'>{_inline(stripped[2:])}"
                f"</blockquote>"
            )
        else:
            html_parts.append(f"<p>{_inline(stripped)}</p>")

    if in_list:
        html_parts.append("</ul>")
    if in_code_block:
        html_parts.append("</code></pre>")

    return "\n".join(html_parts)


def _inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code, links)."""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    return text


def _build_page(kb_dir: Path, filename: str | None = None) -> str:
    """Build the full HTML page for a given file or the index."""
    md_files = list_md_files(kb_dir)
    md_files = [f for f in md_files if f.name.upper() != "WIKI.MD"]

    sidebar_links: list[str] = []
    sidebar_links.append(
        f'<a href="/" class="{"active" if filename is None else ""}">WIKI Index</a>'
    )
    for f in md_files:
        active = "active" if f.name == filename else ""
        sidebar_links.append(f'<a href="/{f.name}" class="{active}">{f.stem}</a>')

    total_files = len(md_files)
    total_words = sum(len(read_file_content(f).split()) for f in md_files)

    if filename:
        filepath = kb_dir / filename
        if filepath.exists():
            content_md = read_file_content(filepath)
        else:
            content_md = f"# Not Found\n\nFile `{filename}` does not exist."
    else:
        wiki_path = kb_dir / "WIKI.md"
        if wiki_path.exists():
            content_md = read_file_content(wiki_path)
        else:
            content_md = "# Knowledge Base\n\nNo wiki index generated yet. Use `:wiki` to generate."

    content_html = _md_to_html(content_md)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KB Viewer{(" - " + filename) if filename else ""}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<nav class="sidebar">
<h2>Knowledge Base</h2>
<input type="text" class="search-box" placeholder="Filter topics..."
       oninput="filterTopics(this.value)">
{"".join(sidebar_links)}
<div class="stats">
{total_files} topics &middot; {total_words} words
</div>
</nav>
<main class="main">{content_html}</main>
</div>
<script>
function filterTopics(q) {{
  document.querySelectorAll('.sidebar a').forEach(a => {{
    a.style.display = a.textContent.toLowerCase().includes(q.toLowerCase()) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""


def create_handler(kb_dir: Path) -> type:
    """Create an HTTP request handler for the KB web UI."""

    class KBHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.strip("/")
            if path and path.endswith(".md"):
                filename = path
            elif path and not path.startswith("favicon"):
                filename = path + ".md" if not path.endswith(".md") else path
            else:
                filename = None

            html = _build_page(kb_dir, filename if path else None)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            pass  # Suppress default logging

    return KBHandler


def start_web_ui(kb_dir: Path, port: int = 8899) -> tuple[threading.Thread, int]:
    """Start the web UI server in a background thread.

    Returns (thread, port).
    """
    handler = create_handler(kb_dir)
    server = http.server.HTTPServer(("0.0.0.0", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread, port
