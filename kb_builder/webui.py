"""Built-in web UI viewer for the knowledge base (replaces Obsidian)."""

from __future__ import annotations

import http.server
import re
import threading
from pathlib import Path

from kb_builder.storage import list_md_files, read_file_content
from kb_builder.tasks import load_tasks

CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

:root {
  --bg: #0a0612;
  --panel: #160d29;
  --fg: #e6f1ff;
  --neon-pink: #ff2e97;
  --neon-cyan: #00f0ff;
  --neon-green: #39ff14;
  --neon-yellow: #ffe600;
  --neon-purple: #b14aed;
  --border: #2d1b4e;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'VT323', monospace;
  font-size: 20px;
  background:
    radial-gradient(circle at 20% 10%, rgba(177,74,237,0.15), transparent 40%),
    radial-gradient(circle at 80% 80%, rgba(0,240,255,0.12), transparent 40%),
    var(--bg);
  color: var(--fg);
  line-height: 1.5;
  min-height: 100vh;
}

/* CRT scanline overlay */
body::before {
  content: "";
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    to bottom,
    rgba(0,0,0,0) 0px,
    rgba(0,0,0,0) 2px,
    rgba(0,0,0,0.18) 3px,
    rgba(0,0,0,0) 4px
  );
  pointer-events: none;
  z-index: 9999;
}
/* subtle screen flicker */
body::after {
  content: "";
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(177,74,237,0.02);
  pointer-events: none;
  z-index: 9998;
  animation: flicker 0.15s infinite alternate;
}
@keyframes flicker { from { opacity: 0.95; } to { opacity: 1; } }

.arcade-title {
  font-family: 'Press Start 2P', monospace;
  text-align: center;
  padding: 1.2rem;
  font-size: 1.1rem;
  color: var(--neon-yellow);
  text-shadow: 0 0 6px var(--neon-yellow), 0 0 14px var(--neon-pink);
  letter-spacing: 2px;
  border-bottom: 3px solid var(--neon-pink);
  background: var(--panel);
  position: relative;
  z-index: 1;
}

/* HUD score panel */
.hud {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  flex-wrap: wrap;
  padding: 1rem;
  background: var(--panel);
  border-bottom: 2px solid var(--neon-cyan);
}
.hud .score {
  font-family: 'Press Start 2P', monospace;
  font-size: 0.7rem;
  text-align: center;
  padding: 0.6rem 1rem;
  border: 2px solid var(--border);
  border-radius: 4px;
  background: rgba(0,0,0,0.4);
}
.hud .score .label { color: var(--neon-cyan); display: block; margin-bottom: 0.5rem; }
.hud .score .value { color: var(--neon-green); font-size: 1.1rem;
                     text-shadow: 0 0 8px var(--neon-green); }
.hud .score.pink .value { color: var(--neon-pink); text-shadow: 0 0 8px var(--neon-pink); }
.hud .score.yellow .value { color: var(--neon-yellow); text-shadow: 0 0 8px var(--neon-yellow); }

.container { display: flex; }

.sidebar {
  width: 280px;
  background: var(--panel);
  padding: 1rem;
  border-right: 3px solid var(--neon-purple);
  position: fixed;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  padding-top: 1rem;
}
.sidebar h2 {
  font-family: 'Press Start 2P', monospace;
  color: var(--neon-pink);
  font-size: 0.7rem;
  margin-bottom: 1rem;
  text-shadow: 0 0 6px var(--neon-pink);
}
.sidebar a {
  display: block;
  color: var(--fg);
  text-decoration: none;
  padding: 0.4rem 0.6rem;
  margin-bottom: 4px;
  border: 1px solid transparent;
  border-radius: 3px;
  transition: all 0.1s;
}
.sidebar a::before { content: "> "; color: var(--neon-green); }
.sidebar a:hover, .sidebar a.active {
  color: var(--neon-cyan);
  border-color: var(--neon-cyan);
  background: rgba(0,240,255,0.08);
  text-shadow: 0 0 6px var(--neon-cyan);
}

.main {
  margin-left: 280px;
  padding: 2rem 3rem;
  max-width: 1000px;
  flex: 1;
}

h1 {
  font-family: 'Press Start 2P', monospace;
  color: var(--neon-cyan);
  font-size: 1.2rem;
  margin-bottom: 1.5rem;
  padding-bottom: 0.8rem;
  border-bottom: 2px dashed var(--neon-purple);
  text-shadow: 0 0 8px var(--neon-cyan);
  line-height: 1.6;
}
h2 {
  font-family: 'Press Start 2P', monospace;
  color: var(--neon-green);
  font-size: 0.9rem;
  margin-top: 1.8rem;
  margin-bottom: 0.7rem;
  text-shadow: 0 0 6px var(--neon-green);
}
h3 {
  font-family: 'Press Start 2P', monospace;
  color: var(--neon-yellow);
  font-size: 0.75rem;
  margin-top: 1.2rem;
  margin-bottom: 0.5rem;
  text-shadow: 0 0 5px var(--neon-yellow);
}
p, li { margin-bottom: 0.5rem; }
strong { color: var(--neon-yellow); }
em { color: var(--neon-pink); font-style: normal; }
code {
  background: #000;
  color: var(--neon-green);
  padding: 0.1rem 0.4rem;
  border: 1px solid var(--neon-green);
  border-radius: 3px;
  font-family: 'VT323', monospace;
}
pre {
  background: #000;
  padding: 1rem;
  border: 2px solid var(--neon-purple);
  border-radius: 4px;
  overflow-x: auto;
  margin: 1rem 0;
  box-shadow: 0 0 12px rgba(177,74,237,0.4);
}
pre code { background: none; border: none; padding: 0; }
a { color: var(--neon-cyan); text-shadow: 0 0 4px var(--neon-cyan); }
ul, ol { padding-left: 1.5rem; }
blockquote { color: var(--neon-yellow); }
table { border-collapse: collapse; margin: 1rem 0; width: 100%; }
th, td { border: 1px solid var(--neon-purple); padding: 0.5rem; text-align: left; }
th { background: var(--panel); color: var(--neon-cyan); }

.search-box {
  width: 100%;
  padding: 0.5rem;
  background: #000;
  color: var(--neon-green);
  border: 2px solid var(--neon-green);
  border-radius: 3px;
  margin-bottom: 1rem;
  font-family: 'VT323', monospace;
  font-size: 1rem;
}
.search-box::placeholder { color: rgba(57,255,20,0.5); }

.insert-coin {
  text-align: center;
  font-family: 'Press Start 2P', monospace;
  font-size: 0.6rem;
  color: var(--neon-pink);
  padding: 1rem;
  animation: blink 1s steps(2, start) infinite;
}
@keyframes blink { to { visibility: hidden; } }
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
    try:
        total_tasks = len(load_tasks(kb_dir))
    except Exception:
        total_tasks = 0

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
<title>KB ARCADE{(" - " + filename) if filename else ""}</title>
<style>{CSS}</style>
</head>
<body>
<div class="arcade-title">&#9733; KNOWLEDGE BASE ARCADE &#9733;</div>
<div class="hud">
  <div class="score">
    <span class="label">TOPICS</span>
    <span class="value">{total_files:04d}</span>
  </div>
  <div class="score pink">
    <span class="label">WORDS</span>
    <span class="value">{total_words:06d}</span>
  </div>
  <div class="score yellow">
    <span class="label">TASKS</span>
    <span class="value">{total_tasks:04d}</span>
  </div>
</div>
<div class="container">
<nav class="sidebar">
<h2>SELECT LEVEL</h2>
<input type="text" class="search-box" placeholder="search topics..."
       oninput="filterTopics(this.value)">
{"".join(sidebar_links)}
</nav>
<main class="main">
{content_html}
<div class="insert-coin">&#9654; INSERT COIN TO CONTINUE &#9664;</div>
</main>
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
