# High-Level Design

## System Overview

The Terminal Knowledge Base Builder is a CLI application that captures user input, classifies it using an LLM, and maintains an organized markdown-based knowledge base with an auto-generated wiki index.

```mermaid
graph TB
    subgraph User Interface
        A[Terminal Input Loop]
        B[Rich Console UI]
    end

    subgraph Core Engine
        C[LLM Classifier<br/>LiteLLM + GPT-4o-mini]
        D[Storage Manager]
        E[Wiki Generator]
    end

    subgraph Knowledge Base
        F[python.md]
        G[docker.md]
        H[git.md]
        I[...]
        J[WIKI.md]
    end

    A -->|User types text| C
    C -->|topic, filename, markdown| D
    D -->|Append content| F
    D -->|Append content| G
    D -->|Append content| H
    D -->|Append content| I
    E -->|Regenerate index| J
    B -->|Display feedback| A

    style A fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#4CAF50,color:#fff
    style E fill:#9C27B0,color:#fff
    style J fill:#F44336,color:#fff
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant TUI as Terminal UI
    participant LLM as LiteLLM
    participant S as Storage
    participant W as Wiki Generator

    U->>TUI: Types knowledge input
    TUI->>LLM: Send text for classification
    LLM-->>TUI: {topic, filename, markdown}
    TUI->>S: Append markdown to file
    S-->>TUI: Confirm save
    TUI-->>U: Show topic + file feedback

    Note over W: Background thread<br/>(every 60s)
    W->>S: Read all markdown files
    S-->>W: File contents
    W->>W: Generate WIKI.md index
    W-->>TUI: Auto-regen notification
```

## Component Interactions

```mermaid
graph LR
    subgraph Input Layer
        CLI[CLI Args Parser]
        REPL[Input REPL Loop]
        CMD[Command Handler<br/>:wiki :stats :show :quit]
    end

    subgraph Processing Layer
        LLM[LiteLLM Classifier]
        FMT[Markdown Formatter]
    end

    subgraph Persistence Layer
        FS[File System Storage]
        WIKI[Wiki Index Generator]
    end

    CLI --> REPL
    REPL --> CMD
    REPL --> LLM
    LLM --> FMT
    FMT --> FS
    FS --> WIKI
    CMD --> WIKI
    CMD --> FS

    style LLM fill:#FF9800,color:#fff
    style FS fill:#4CAF50,color:#fff
    style WIKI fill:#9C27B0,color:#fff
```
