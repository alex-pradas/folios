# Folios

A simple MCP server that gives AI assistants access to your document library.

Point it at a folder of Markdown files, and your AI assistant can browse, search, and compare document versions. It is a poor's man’s document management system designed for easy integration with AI tools. You only need a folder of properly formatted Markdown files as your source. 

This tool is ideal for teams wanting to leverage AI for document retrieval and analysis without complex setups. It does not manage the approval cycle or enforce workflows; it simply provides structured access to your documents. It does not version control your files, that has to be done externally (e.g., Git, manual versioning).

## What It Does

Folios provides **5 MCP tools** for document management:

| Tool | Description |
|------|-------------|
| `get_document` | Retrieve document content |
| `get_document_metadata` | Get structured metadata and chapters |
| `list_documents` | Browse and filter documents |
| `list_versions` | View version history |
| `compare_versions` | Diff between versions |

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

Folios expects Markdown files with a specific structure:

### File Naming

Files must follow the pattern `{id}_v{version}.md`:

```
documents/
├── 100001_v1.md    # Document 100001, version 1
├── 100001_v2.md    # Document 100001, version 2
└── 100002_v1.md    # Document 100002, version 1
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

Once configured, you can ask your AI assistant:

> "List all approved design practices"

> "Show me the latest version of document 100001"

> "What changed between version 1 and version 2 of document 100001?"

> "Find all documents by John Smith"

## More Information

- [Tools Reference](tools/index.md) - Detailed tool documentation
- [Document Format](document-format.md) - Full format specification
- [Configuration](configuration.md) - Environment variables and deployment options
