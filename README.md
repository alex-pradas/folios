# Folios

[![PyPI version](https://badge.fury.io/py/folios.svg)](https://badge.fury.io/py/folios)
[![Tests](https://github.com/alex-pradas/folios/actions/workflows/publish.yml/badge.svg)](https://github.com/alex-pradas/folios/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/alex-pradas/folios/branch/main/graph/badge.svg)](https://codecov.io/gh/alex-pradas/folios)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Model Context Protocol (MCP) server for versioned document management. Folios provides AI agents with access to your document library.

## Features

- **Versioned Documents** - Store multiple versions of documents with simple `{id}_v{version}.md` naming
- **Rich Metadata** - YAML frontmatter with author, reviewer, approver, status, and type
- **Auto-parsed Chapters** - H1/H2 headings automatically extracted as document structure
- **Version Comparison** - Generate diffs between any two versions
- **Flexible Filtering** - Query documents by status, type, or author

## Installation

```bash
# Using uvx (recommended)
uvx folios

# Using pip
pip install folios
```

## Quick Start

### 1. Create your documents folder

Documents follow the naming convention `{id}_v{version}.md`:

```
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

# Introduction

Your document content here...

## Background

More content...
```

### 3. Run the server

```bash
export FOLIOS_PATH=/path/to/your/documents
folios
```

Or with uvx:

```bash
FOLIOS_PATH=/path/to/docs uvx folios
```

## MCP Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `get_document` | `id`, `version?` | Retrieve document content (latest if version omitted) |
| `get_document_metadata` | `id`, `version?` | Get metadata including auto-parsed chapters |
| `compare_versions` | `id`, `old_version`, `new_version` | Diff between two versions |
| `list_documents` | `status?`, `type?`, `author?` | List documents with optional filters |
| `list_versions` | `id` | List all versions of a document |

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

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `FOLIOS_PATH` | Path to documents folder | `./documents` |

## Example Usage with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios"],
      "env": {
        "FOLIOS_PATH": "/path/to/your/documents"
      }
    }
  }
}
```

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

MIT
