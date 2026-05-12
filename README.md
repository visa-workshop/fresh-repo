# Terminal Knowledge Base Builder

A terminal application that listens to your input, uses an LLM (via [LiteLLM](https://docs.litellm.ai/)) to classify and organize it, and maintains a structured markdown knowledge base with an auto-generated wiki index.

## How It Works

1. **You type** anything into the terminal — notes, facts, code snippets, ideas
2. **LLM detects intent** — whether you're storing knowledge or asking a question
3. **Stores**: LLM classifies input, determines topic, appends to the right markdown file
4. **Queries**: LLM searches your KB and answers from stored knowledge
5. **Ingest**: Import raw documents or clip web articles into the KB via LLM compilation
6. **Wiki is auto-regenerated** periodically with backlinks and cross-references
7. **Lint**: LLM health checks find inconsistencies, gaps, and suggest connections
8. **Web UI**: Built-in viewer to browse your KB in the browser

## Installation

```bash
# Clone and install
pip install -e .
```

## Configuration

### API Key (required)

Set your OpenAI API key:

```bash
export OPENAI_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

### LLM Model (optional)

By default the app uses `gpt-4o-mini`. You can change the model via environment variable or CLI flag:

```bash
# Via environment variable
export LITELLM_MODEL="gpt-4o"

# Or via CLI flag
kb-builder --model gpt-4o
kb-builder -m claude-3-haiku-20240307
```

Since this app uses [LiteLLM](https://docs.litellm.ai/docs/providers), you can use any model from any supported provider. Some examples:
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **Anthropic**: `claude-3-haiku-20240307`, `claude-3-sonnet-20240229`
- **Azure OpenAI**: `azure/my-deployment-name`
- **Ollama (local)**: `ollama/llama3`, `ollama/mistral`
- **AWS Bedrock**: `bedrock/anthropic.claude-3-sonnet-20240229-v1:0`

The CLI `--model` flag takes priority over the `LITELLM_MODEL` environment variable.

### Custom Base URL (optional)

If you're using a custom LLM endpoint (corporate proxy, Azure OpenAI, local LLM server, etc.), set the base URL:

```bash
# Using LiteLLM-specific variable (recommended)
export LITELLM_BASE_URL="https://your-proxy.company.com/v1"

# Or using OpenAI-compatible variable
export OPENAI_BASE_URL="https://your-proxy.company.com/v1"
```

Common use cases:
- **Corporate API proxy**: `https://api-gateway.internal.company.com/openai/v1`
- **Azure OpenAI**: `https://your-resource.openai.azure.com`
- **Local LLM (Ollama, vLLM, etc.)**: `http://localhost:11434/v1`
- **LiteLLM proxy server**: `http://localhost:4000`

### Custom CA Bundle (optional)

If your corporate environment uses a custom/internal Certificate Authority (CA), attach your CA bundle so TLS verification works:

```bash
# Standard environment variable (works with most Python HTTP libraries)
export REQUESTS_CA_BUNDLE="/path/to/your/ca-bundle.crt"

# Or using the OpenSSL-compatible variable
export SSL_CERT_FILE="/path/to/your/ca-bundle.crt"
```

This is commonly needed when:
- Your organization uses a corporate TLS inspection proxy
- You're connecting through a VPN with custom certificates
- Your API endpoint uses an internal/self-signed certificate

The CA bundle file should be a PEM-formatted file containing one or more CA certificates. You can typically get this from your IT department or export it from your system's certificate store.

### Full Corporate Setup Example

```bash
# API key
export OPENAI_API_KEY="sk-..."

# Route through corporate proxy
export LITELLM_BASE_URL="https://api-gateway.internal.company.com/openai/v1"

# Use corporate CA bundle for TLS
export REQUESTS_CA_BUNDLE="/etc/ssl/certs/corporate-ca-bundle.crt"

# Use a custom model
kb-builder --model gpt-4o

# Start the knowledge base builder
kb-builder
```

### Environment Variables Reference

| Variable             | Required | Description                                      |
|----------------------|----------|--------------------------------------------------|
| `OPENAI_KEY`         | Yes*     | OpenAI API key                                   |
| `OPENAI_API_KEY`     | Yes*     | OpenAI API key (alternative)                     |
| `LITELLM_MODEL`      | No       | LLM model name (default: `gpt-4o-mini`)           |
| `LITELLM_BASE_URL`   | No       | Custom LLM API base URL                          |
| `OPENAI_BASE_URL`    | No       | Custom base URL (OpenAI-compatible alternative)   |
| `REQUESTS_CA_BUNDLE` | No       | Path to custom CA certificate bundle (PEM format) |
| `SSL_CERT_FILE`      | No       | Path to CA certificate file (alternative)         |

\* At least one of `OPENAI_KEY` or `OPENAI_API_KEY` must be set.

## Usage

```bash
# Start the knowledge base builder
kb-builder

# Use a custom directory
kb-builder -d /path/to/my/knowledge-base

# Set wiki regeneration interval (default: 60s)
kb-builder --wiki-interval 30

# Start with web UI viewer
kb-builder --web

# Custom web UI port
kb-builder --web --web-port 9090
```

### Commands

| Command            | Description                                     |
|--------------------|--------------------------------------------------|
| `:wiki`            | Regenerate the wiki index now                    |
| `:stats`           | Show knowledge base statistics                   |
| `:show`            | Display the current wiki index                   |
| `:ingest <path>`   | Ingest a file or directory into the KB            |
| `:clip <url>`      | Clip a web article and ingest into the KB         |
| `:search <query>`  | Full-text search across all KB content            |
| `:lint`            | Run LLM health checks on the KB                  |
| `:save`            | File the last query answer back into the KB       |
| `:task <text>`     | Log a timestamped task/activity                   |
| `:tasks`           | Show recent task entries                          |
| `:daily`           | Generate AI-powered daily summary                 |
| `:weekly`          | Generate AI-powered weekly summary                |
| `:web`             | Start the built-in web UI viewer                  |
| `:help`            | Show help message                                 |
| `:quit`            | Exit the application                              |

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

kb> what do I know about Python?

  Answer:
  Python lists are mutable sequences that support indexing and slicing.
  Use :save to file this answer into the KB

kb> :save

  Answer filed: Python
  File:        python-answers.md

kb> :clip https://docs.python.org/3/glossary.html

  Clipped: https://docs.python.org/3/glossary.html
  Topic:   Python Glossary
  File:    python-glossary.md

kb> :search decorator

  Found 2 match(es) for 'decorator':
  python.md (line 3): Decorators are functions that modify other functions.

kb> :ingest ./my_notes/

  Ingested 5 files.

kb> :lint

  Health Score: 7/10
  Missing Data:
    - Examples of decorators in use
  Connection Suggestions:
    - Link 'Python' and 'Python Glossary' articles

kb> :task Fixed the authentication bug in login service

  Task logged: Fixed the authentication bug in login service
  2025-01-15 10:30 UTC

kb> :task Reviewed PR #42 for the data pipeline team

  Task logged: Reviewed PR #42 for the data pipeline team
  2025-01-15 14:15 UTC

kb> :tasks

  Recent Task Entries:
  Wed 2025-01-15 10:30  Fixed the authentication bug in login service
  Wed 2025-01-15 14:15  Reviewed PR #42 for the data pipeline team

kb> :weekly

  Weekly Summary:
  ## Major Deliverables
  - Fixed authentication bug in login service
  ## Team Contributions
  - Reviewed PR #42 for the data pipeline team

kb> :web
  Web UI started at http://localhost:8899

kb> :stats
Knowledge Base Statistics:
  python.md: 8 lines
  docker.md: 6 lines
  python-glossary.md: 32 lines

kb> :wiki
Wiki index regenerated: knowledge_base/WIKI.md
```

The app automatically detects whether you're **storing knowledge** or **asking a question**:
- Statements, facts, and notes are classified and saved to markdown files
- Questions are answered by searching the knowledge base and using the LLM to synthesize an answer from stored content
- Query answers can be filed back into the KB with `:save` so explorations "add up"
- Use `:task` throughout the day to log activities, then `:weekly` for an AI summary

## Project Structure

```
kb_builder/
├── __init__.py     # Package init
├── main.py         # Terminal input loop + command handling
├── llm.py          # LiteLLM classification, intent detection, Q&A
├── storage.py      # Markdown file read/write management
├── wiki.py         # Wiki index generator with backlinks
├── ingest.py       # Raw document ingestion via LLM compilation
├── clip.py         # Web article clipping and ingestion
├── search.py       # Full-text search across KB content
├── lint_kb.py      # LLM-powered KB health checks
├── tasks.py        # Timestamped task tracker with weekly summaries
└── webui.py        # Built-in web UI viewer
docs/
├── HIGH_LEVEL_DESIGN.md   # System architecture (Mermaid diagrams)
└── LOW_LEVEL_DESIGN.md    # Module-level design (Mermaid diagrams)
knowledge_base/     # Default directory for markdown files
```

## Architecture

- **Input Loop**: Rich-powered terminal prompt that captures user text and commands
- **Intent Detection**: LLM determines if input is knowledge to store or a question to answer
- **LLM Classification**: Statements are classified via LiteLLM and routed to the correct markdown file
- **Query Answering**: Questions are answered from stored knowledge; answers can be filed back into the KB
- **Data Ingest**: Raw documents (text, code, markdown) are compiled by the LLM into structured KB entries
- **Web Clipping**: Web articles are fetched, converted to markdown, and ingested via LLM compilation
- **Search**: Full-text search across all KB content with context highlighting
- **Linting**: LLM-powered health checks find inconsistencies, missing data, integrity issues, and suggest connections
- **Storage Layer**: Manages markdown files — creates new files with title headers, appends formatted content
- **Wiki Generator**: Builds `WIKI.md` with table of contents, section listings, backlinks, word counts, and timestamps
- **Task Tracker**: Timestamped activity logging with AI-generated daily and weekly summaries
- **Web UI**: Built-in HTTP server with dark-themed viewer, sidebar navigation, and topic filtering
