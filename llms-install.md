# Installing Folios MCP Server

Folios is a local MCP server for querying versioned Markdown documents.

## Prerequisites

- Python 3.10 or later
- `uv` package manager (recommended) or `pip`

## Installation

### Option 1: Using uvx (recommended)

No installation needed. Just configure the MCP server:

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

Replace `/path/to/your/documents` with the actual path to a folder containing Markdown files.

### Option 2: Using pip

```bash
pip install folios
```

Then configure:

```json
{
  "mcpServers": {
    "folios": {
      "command": "folios",
      "args": ["--path", "/path/to/your/documents"]
    }
  }
}
```

### Option 3: Using environment variable

Set `FOLIOS_PATH` in your shell profile instead of using `--path`:

```bash
export FOLIOS_PATH=/path/to/your/documents
```

Then the MCP config simplifies to:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios"]
    }
  }
}
```

## Document Format

Documents must follow the naming convention `{id}_v{version}.md` (e.g., `123456_v1.md`). Optional YAML frontmatter provides metadata:

```markdown
---
author: "J. Smith"
date: "2025-01-15"
document_type: "Design Practice"
status: "Approved"
---

# Document Title

## Chapter 1

Content here...
```

## Available Tools

- `browse_catalog` - List documents with optional filters
- `get_document_content` - Retrieve full document content
- `get_document_metadata` - Get document metadata and chapters
- `get_chapter_content` - Retrieve a specific chapter (H2 section)
- `diff_document_versions` - Compare two versions of a document
- `list_revisions` - List all versions of a document
