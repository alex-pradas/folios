# Folios

<p align="center">
  <img src="https://raw.githubusercontent.com/alex-pradas/folios/main/folio_logo.png" alt="Folios Logo" width="120">
</p>

[![PyPI version](https://badge.fury.io/py/folios.svg)](https://badge.fury.io/py/folios)
[![Tests](https://github.com/alex-pradas/folios/actions/workflows/publish.yml/badge.svg)](https://github.com/alex-pradas/folios/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/alex-pradas/folios/branch/main/graph/badge.svg)](https://codecov.io/gh/alex-pradas/folios)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://alex-pradas.github.io/folios/)

A lightweight Model Context Protocol (MCP) server for querying your local library of documents.

![Example](https://raw.githubusercontent.com/alex-pradas/folios/main/example.png)

**[Documentation](https://alex-pradas.github.io/folios/)**

## What problem does Folios solve?

AI agents working on engineering tasks often need access to internal documents—design practices, guidelines, specifications—typically stored in document management systems (PLM, QMS...). While RAG (Retrieval Augmented Generation) can provide this functionality, it's complex to set up and maintain.

Why not access the documents directly? LLM context windows are big enough to handle these documents, or at least whole sections. Also, the master information lives in these documents anyway, AIs or RAGs won't replace the quality processes companies already use to manage knowledge.  Giving agents read-only access to the source library is a more straightforward approach. However, enterprise document repositories often have restricted APIs or require privileged access that's difficult to obtain.

**Folios solves this by providing a simple MCP server that points to a folder of Markdown files.** If you're developing agentic workflows and need to mock or prototype document access before integrating with complex enterprise systems, Folios lets AI assistants query documents with minimal setup.

No RAG pipelines, no finetuning, no extra steps. From source to context window.

## Features

- **Zero Config** - Just point to a folder of Markdown files and go
- **Local First** - Your documents stay on your machine or network, no cloud dependencies
- **Flexible Metadata** - Use any frontmatter fields your workflow needs
- **Versioned Documents** - Store multiple versions with simple `{id}_v{version}.md` naming
- **Chapter Extraction** - Retrieve specific sections without loading entire documents
- **Version Diffing** - Compare changes between document versions, grouped by chapter
- **MCP Resources** - Browse documents as native MCP resources

## One-liner to install, run and configure

```bash
uvx folios --path /path/to/your/documents
```

## Quick guide to get started

### 1. Create your documents folder

Any normal local folder will do. Documents follow the naming convention `{id}_v{version}.md`:

```folder
documents/
├── 123456_v1.md
├── 123456_v2.md
└── 789012_v1.md
```

### 2. Add YAML frontmatter to each document

Frontmatter is flexible - include any fields your workflow requires:

```markdown
---
author: "J. Smith"
date: "2025-01-15"
document_type: "Design Practice"
status: "Approved"
reviewer: "A. Johnson"
---

# Stress Analysis Design Practice

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Background

More text here...
```

Only the `---` delimiters, an H1 title, and the `{id}_v{version}.md` filename pattern are required. Missing fields show "NA" in responses.

### 3. Run the server

You can run folios directly with one terminal command:

```bash
uvx folios --path /path/to/your/documents
```

alternatively, you can add it to your LLM Client MCP configuration:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios", "--path", "/path/to/your/documents"]
    }
  }
}
```

We have tested it with [Claude Desktop](https://claude.ai/desktop) and the [GitHub Copilot Extension for VS Code](https://code.visualstudio.com/docs/copilot/overview), but it should work with any MCP-compatible client.

## MCP Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `get_document_content` | `document_id`, `version?` | Retrieve document content (latest if version omitted) |
| `get_document_metadata` | `document_id`, `version?` | Get metadata including auto-parsed chapters |
| `get_chapter_content` | `document_id`, `chapter_title`, `version?` | Retrieve content of a specific chapter (H2 section) |
| `diff_document_versions` | `document_id`, `from_version`, `to_version` | Diff between two versions, grouped by chapter |
| `browse_catalog` | `status?`, `document_type?`, `author?` | List documents with optional filters |
| `list_revisions` | `document_id` | List all versions of a document |

## Document Schema

### Core Metadata Fields

These fields are always present in metadata responses:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique document identifier (from filename) |
| `version` | int | Version number (from filename) |
| `title` | str | Document title (from H1 heading) |
| `author` | str | Document author ("NA" if not in frontmatter) |
| `date` | str | Publication date ("NA" if not in frontmatter) |
| `chapters` | list | Auto-parsed from H2 headings |

### Dynamic Fields

Any additional frontmatter fields are included in metadata responses. Common examples:

- `document_type` - Document type (Design Practice, Guideline, etc.)
- `status` - Document status (Draft, Approved, etc.)
- `reviewer`, `approver` - Approval workflow fields
- Custom fields for your specific workflow

## Configuration

### Documents Path

Provide the documents folder path via CLI flag or environment variable:

| Option | Description |
|--------|-------------|
| `--path` | Path to documents folder (CLI flag) |
| `FOLIOS_PATH` | Path to documents folder (environment variable) |

## Limitations

Folios is intentionally minimal. It does **not** provide:

- **Full-text search** - Use `browse_catalog` filters or let your LLM search within retrieved content
- **Write operations** - Documents are read-only; edit them with your normal tools
- **Authentication** - No access control; secure your documents folder via filesystem permissions
- **Real-time updates** - Schema discovery happens at startup; restart to pick up new documents
- **Non-Markdown formats** - Only `.md` files are supported

## Development

```bash
git clone https://github.com/alex-pradas/folios
cd folios
uv sync

# Run locally
FOLIOS_PATH=./examples/documents uv run folios

# Run tests
uv run pytest
```

## License

This project is licensed under the terms of the MIT license.
