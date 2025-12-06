# Folios

A simple MCP server that gives AI assistants access to your document library.

Point it at a folder of Markdown files, and your AI assistant can browse, search, and compare document versions. It is a poor's man’s document management system designed for easy integration with AI tools. You only need a folder of properly formatted Markdown files as your source. 

This tool is ideal if you want to give your LLM based Agent read-only access without complex setups. It does not manage the approval cycle or enforce workflows; it simply provides structured access to your documents. It does not version control your files, that has to be done externally (e.g., Git, manual versioning).

## Why Folios?

This tool is to mock access to more complex document management engineering systems (think SAP, PTC Windchill, Siemens TeamCenter...). It is designed for simplicity and ease of use, not for production use in regulated environments.

## What It Does

Folios provides **5 MCP tools** for document management:

| Tool | Description |
|------|-------------|
| `get_document_content` | Retrieve document content |
| `get_document_metadata` | Get structured metadata and chapters |
| `list_documents` | Browse and filter documents |
| `list_document_versions` | View version history |
| `diff_document_versions` | Diff between versions |

## Quick Setup

### Claude Desktop

Add to your Claude Desktop config:

=== "macOS"

    Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "folios": {
          "command": "uvx",
          "args": ["folios-mcp"],
          "env": {
            "FOLIOS_PATH": "/path/to/your/documents"
          }
        }
      }
    }
    ```

=== "Windows"

    Edit `%APPDATA%\Claude\claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "folios": {
          "command": "uvx",
          "args": ["folios-mcp"],
          "env": {
            "FOLIOS_PATH": "C:\\path\\to\\your\\documents"
          }
        }
      }
    }
    ```

=== "Linux"

    Edit `~/.config/claude/claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "folios": {
          "command": "uvx",
          "args": ["folios-mcp"],
          "env": {
            "FOLIOS_PATH": "/path/to/your/documents"
          }
        }
      }
    }
    ```

### VS Code (Claude Extension)

Add to your VS Code settings or `.mcp.json`:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios-mcp"],
      "env": {
        "FOLIOS_PATH": "/path/to/your/documents"
      }
    }
  }
}
```

### Standalone (for testing)

```bash
FOLIOS_PATH=/path/to/docs uvx folios-mcp
```

## Document Requirements

Folios expects that the selected folder contains Markdown files with a specific structure:

### File Naming

Files must follow the pattern `{id}_v{version}.md`:

```
documents/
├── 123456_v1.md    # Document 123456, version 1
├── 123456_v2.md    # Document 123456, version 2
└── 789012_v1.md    # Document 789012, version 1
```

### YAML Frontmatter

Each document needs YAML frontmatter with metadata:

```markdown
---
type: Design Practice
author: John Smith
reviewer: Jane Doe
approver: Bob Wilson
date: 2025-01-15
status: Approved
---

# Document Title

Your content here...

## Section One

More content...
```

**Required fields:** `type`, `author`, `reviewer`, `approver`, `date`, `status`

**Title:** The first `#` heading becomes the document title.

**Chapters:** All `##` headings are extracted as chapters.

## Supported Values

### Document Types

- `Design Practice`
- `Guideline`
- `Best Practice`
- `TRS` (Technical Requirement Specification)
- `DVP` (Design Verification Plan)
- `DVR` (Detail Verification Review)

### Document Statuses

- `Draft`
- `In Review`
- `Approved`
- `Withdrawn`

## Example Interaction

### List approved design practices

**Tool call:**
```json
{
  "tool": "list_documents",
  "parameters": {
    "status": "Approved",
    "document_type": "Design Practice"
  }
}
```

**Response:**
```json
[
  {
    "id": 123456,
    "title": "Introduction",
    "latest_version": 2,
    "status": "Approved",
    "type": "Design Practice"
  }
]
```

### Get document metadata

**Tool call:**
```json
{
  "tool": "get_document_metadata",
  "parameters": {
    "document_id": 123456
  }
}
```

**Response:**
```json
{
  "metadata": {
    "id": 123456,
    "version": 2,
    "title": "Introduction",
    "type": "Design Practice",
    "author": "J. Smith",
    "reviewer": "A. Johnson",
    "approver": "M. Williams",
    "date": "2025-02-15",
    "status": "Approved",
    "chapters": [
      {"title": "Purpose"},
      {"title": "Scope"},
      {"title": "Static Analysis"},
      {"title": "Fatigue Analysis"},
      {"title": "Thermal Analysis"}
    ]
  }
}
```

### Diff document versions

**Tool call:**
```json
{
  "tool": "diff_document_versions",
  "parameters": {
    "document_id": 123456,
    "from_version": 1,
    "to_version": 2
  }
}
```

**Response:**
```json
{
  "diff": "--- 123456_v1.md\n+++ 123456_v2.md\n@@ -1,12 +1,12 @@\n ---\n id: 123456\n-version: 1\n+version: 2\n..."
}
```

### List document versions

**Tool call:**
```json
{
  "tool": "list_document_versions",
  "parameters": {
    "document_id": 123456
  }
}
```

**Response:**
```json
{
  "versions": [
    {
      "version": 1,
      "date": "2025-01-10",
      "status": "Approved",
      "author": "J. Smith"
    },
    {
      "version": 2,
      "date": "2025-02-15",
      "status": "Approved",
      "author": "J. Smith"
    }
  ]
}
```

## More Information

- [Tools Reference](tools/index.md) - Detailed tool documentation
- [Document Format](document-format.md) - Full format specification
- [Configuration](configuration.md) - Environment variables and deployment options
