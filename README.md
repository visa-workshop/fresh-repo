# Terminal Knowledge Base Builder

A terminal application that listens to your input, uses an LLM (via [LiteLLM](https://docs.litellm.ai/)) to classify and organize it, and maintains a structured markdown knowledge base with an auto-generated wiki index.

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

kb> what do I know about Python?

  Answer:
  You know that Python lists are mutable sequences that support indexing and slicing.

kb> :stats
Knowledge Base Statistics:
  python.md: 8 lines
  docker.md: 6 lines

kb> :wiki
Wiki index regenerated: knowledge_base/WIKI.md
```

The app automatically detects whether you're **storing knowledge** or **asking a question**:
- Statements, facts, and notes are classified and saved to markdown files
- Questions are answered by searching the knowledge base and using the LLM to synthesize an answer from stored content

## Project Structure

```
kb_builder/
├── __init__.py     # Package init
├── main.py         # Terminal input loop + periodic wiki regen
├── llm.py          # LiteLLM classification and routing
├── storage.py      # Markdown file read/write management
└── wiki.py         # Wiki index generator
docs/
├── HIGH_LEVEL_DESIGN.md   # System architecture (Mermaid diagrams)
└── LOW_LEVEL_DESIGN.md    # Module-level design (Mermaid diagrams)
knowledge_base/     # Default directory for markdown files
```

## Architecture

- **Input Loop**: Rich-powered terminal prompt that captures user text
- **Intent Detection**: LLM determines if input is knowledge to store or a question to answer
- **LLM Classification**: Statements are classified via LiteLLM and routed to the correct markdown file. Supports custom base URLs and CA bundles for corporate/private deployments.
- **Query Answering**: Questions are answered by loading all KB content and using the LLM to synthesize an answer from stored knowledge only
- **Storage Layer**: Manages markdown files — creates new files with title headers, appends formatted content
- **Wiki Generator**: Builds `WIKI.md` with table of contents, section listings, word counts, and timestamps. Runs automatically on a configurable interval via a background thread
