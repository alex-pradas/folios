# Folios

[![PyPI version](https://badge.fury.io/py/folios.svg)](https://badge.fury.io/py/folios)
[![Tests](https://github.com/alex-pradas/folios/actions/workflows/publish.yml/badge.svg)](https://github.com/alex-pradas/folios/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/alex-pradas/folios/branch/main/graph/badge.svg)](https://codecov.io/gh/alex-pradas/folios)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A ligthweight Model Context Protocol (MCP) server for giving agents the tools to query your local library of documents.

## What problem solves folios?

When working in engineering applications, AI agents often need access to a variety of internal documents such as design practices, guidelines, and specifications that are stored in a local, document-based knowledge management system. While Retreival Augmented Generation (RAG) implementation can provide such functionality, setting it up and maintaining it up to date can be complex and time-consuming. Why not accessing the documents directly? If the master information is stored in documents, Agentic AI is not going to change the quality processes that are already in place to manage knowledge in companies, so I believe in giving agents read-only access to the document library is a more straightforward approach. However, giving agent access to those system repositories con be challenging due to the restricted nature of their APIs or the lack of privileged access.

If you are developing agentic workflows, in order to mock the functionality to give agents the access to such complex management systems, Folios provides a simple MCP server that can be pointed to a folder of properly formatted Markdown files. This allows AI assistants to perform the same query behaviour with a very low setup cost from the user/developer side.

## Features

- **Zero Config** - Just point to a folder of Markdown files and go
- **Local First** - Your documents stay on your machine or network, no cloud dependencies
- **Minimal Maintenance** - No complex setup, no database, no indexing, all within the document.
- **Versioned Documents** - Store multiple versions with simple `{id}_v{version}.md` naming

## Quick Setup

```bash
uvx folios --folios-path /path/to/your/documents
```

## Quick Start

### 1. Create your documents folder

Any normal local folder will do. Documents follow the naming convention `{id}_v{version}.md`:

```folder
documents/
├── 123456_v1.md
├── 123456_v2.md
└── 789012_v1.md
```

### 2. Add YAML frontmatter to each document

```markdown
---
id: 123456
version: 1
title: "Stress Analysis Design Practice"
type: "Design Practice"
author: "J. Smith"
reviewer: "A. Johnson"
approver: "M. Williams"
date: "2025-01-15"
status: "Approved"
---

# This is the Document Title

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Background

More text here...
```

### 3. Run the server

you can run folios directly with one terminal command

```bash
uvx folios --folios-path /path/to/your/documents
```

alternatively, you can add it to your LLM Client MCP configuration:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios", "--folios-path", "/path/to/your/documents"],
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
| `diff_document_versions` | `document_id`, `from_version`, `to_version` | Diff between two versions |
| `list_documents` | `status?`, `document_type?`, `author?` | List documents with optional filters |
| `list_document_versions` | `document_id` | List all versions of a document |

## Document Schema

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique document identifier |
| `version` | int | Version number (sequential integers) |
| `title` | str | Document title |
| `type` | str | Document type |
| `author` | str | Document author |
| `reviewer` | str | Document reviewer |
| `approver` | str | Document approver |
| `date` | str | Date (ISO format recommended) |
| `status` | str | Document status |
| `chapters` | list | Auto-parsed from H1/H2 headings |

### Document Types

- `Design Practice` - Standard design methodology
- `Guideline` - Recommended approaches
- `Best Practice` - Industry best practices
- `TRS` - Technical Requirement Specification
- `DVP` - Design Verification Plan
- `DVR` - Detail Verification Review

### Document Statuses

- `Draft` - Work in progress
- `In Review` - Under review
- `Approved` - Approved for use
- `Withdrawn` - No longer valid

## Configuration

Provide the documents folder path via CLI flag or environment variable:

| Option | Description |
|--------|-------------|
| `--folios-path` | Path to documents folder (CLI flag) |
| `FOLIOS_PATH` | Path to documents folder (environment variable) |

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
