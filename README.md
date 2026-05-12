# Terminal Knowledge Base Builder

A terminal application that listens to your input, uses an LLM (OpenAI) to classify and organize it, and maintains a structured markdown knowledge base with an auto-generated wiki index.

## How It Works

1. **You type** anything into the terminal — notes, facts, code snippets, ideas
2. **LLM classifies** your input, determining the topic and target markdown file
3. **Content is appended** to the appropriate markdown file with proper formatting
4. **Wiki is auto-regenerated** periodically, keeping an up-to-date index of all topics

## Installation

```bash
# Clone and install
pip install -e .
```

## Setup

Set your OpenAI API key:

```bash
export OPENAI_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

## Usage

```bash
# Start the knowledge base builder
kb-builder

# Use a custom directory
kb-builder -d /path/to/my/knowledge-base

# Set wiki regeneration interval (default: 60s)
kb-builder --wiki-interval 30
```

### Commands

| Command  | Description                        |
|----------|------------------------------------|
| `:wiki`  | Regenerate the wiki index now      |
| `:stats` | Show knowledge base statistics     |
| `:show`  | Display the current wiki index     |
| `:help`  | Show help message                  |
| `:quit`  | Exit the application               |

### Example Session

```
kb> Python lists are mutable sequences that support indexing and slicing

  Topic: Python
  File:  python.md
  Saved to knowledge_base/python.md

kb> Docker containers share the host OS kernel unlike virtual machines

  Topic: Docker
  File:  docker.md
  Saved to knowledge_base/docker.md

kb> :stats
Knowledge Base Statistics:
  python.md: 8 lines
  docker.md: 6 lines

kb> :wiki
Wiki index regenerated: knowledge_base/WIKI.md
```

## Project Structure

```
kb_builder/
├── __init__.py     # Package init
├── main.py         # Terminal input loop + periodic wiki regen
├── llm.py          # OpenAI classification and routing
├── storage.py      # Markdown file read/write management
└── wiki.py         # Wiki index generator
knowledge_base/     # Default directory for markdown files
```

## Architecture

- **Input Loop**: Rich-powered terminal prompt that captures user text
- **LLM Classification**: Each input is sent to OpenAI (`gpt-4o-mini`) which returns a JSON response with topic, filename, and formatted markdown
- **Storage Layer**: Manages markdown files — creates new files with title headers, appends formatted content
- **Wiki Generator**: Builds `WIKI.md` with table of contents, section listings, word counts, and timestamps. Runs automatically on a configurable interval via a background thread
