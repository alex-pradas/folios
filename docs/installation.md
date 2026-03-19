# Installation

Folios is a Python package available on [PyPI](https://pypi.org/project/folios/). It runs as a local MCP server — no cloud services, no network requests. Your documents stay on your machine.

## Prerequisites

- Python 3.10 or later
- A folder of Markdown documents following the `{id}_v{version}.md` naming convention

## Quick start

The fastest way to run Folios:

```bash
uvx folios --path /path/to/your/documents
```

This downloads and runs Folios in one command using [uv](https://docs.astral.sh/uv/). No installation step needed.

Alternatively, install with pip:

```bash
pip install folios
folios --path /path/to/your/documents
```

## Documents path

Folios needs to know where your documents live. You can provide this via:

| Method | Example |
|--------|---------|
| CLI flag | `uvx folios --path /path/to/docs` |
| Environment variable | `export FOLIOS_PATH=/path/to/docs` |

The environment variable is useful when configuring Folios as an MCP server in a client, so you don't need to hardcode the path in each config file.

## MCP client configuration

### Generic MCP configuration

Most MCP-compatible clients use a JSON configuration file. The standard config for Folios:

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

Or using the environment variable:

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

### Claude Desktop

Add to your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

Restart Claude Desktop after saving.

### Claude Code

Folios is available as a Claude Code plugin. Install directly from the marketplace:

```
/plugin marketplace add alex-pradas/folios
/plugin install folios@alex-pradas-folios
```

Set the `FOLIOS_PATH` environment variable in your shell profile before using:

```bash
export FOLIOS_PATH=/path/to/your/documents
```

Alternatively, add Folios manually to your project's `.mcp.json`:

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

### Cursor

Click the button below to install Folios in Cursor with one click:

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=folios&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJmb2xpb3MiXX0%3D)

After installing, open `.cursor/mcp.json` and add the `--path` argument or set `FOLIOS_PATH` in your environment:

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

### VS Code (GitHub Copilot)

Add to your workspace `.vscode/mcp.json` or user `settings.json`:

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

### Windsurf

Add to your Windsurf MCP config at `~/.codeium/windsurf/mcp_config.json`:

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

### Cline

Folios is available in the Cline MCP Marketplace. Open the Extensions panel in Cline, search for "Folios", and install with one click.

For manual configuration, add to your Cline MCP settings:

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

### Codex (OpenAI)

Add to your Codex config at `~/.codex/config.toml`:

```toml
[mcp_servers.folios]
command = "uvx"
args = ["folios", "--path", "/path/to/your/documents"]
```

### Other MCP clients

Any client that supports the Model Context Protocol can use Folios. Use the [generic MCP configuration](#generic-mcp-configuration) above and consult your client's documentation for where to place it.

## Verifying the installation

Once configured, your AI assistant should have access to six tools:

| Tool | Description |
|------|-------------|
| `browse_catalog` | List documents with optional filters |
| `get_document_content` | Retrieve full document content |
| `get_document_metadata` | Get metadata and chapters |
| `get_chapter_content` | Retrieve a specific H2 section |
| `diff_document_versions` | Compare two document versions |
| `list_revisions` | List all versions of a document |

Try asking your AI assistant: *"What documents are available?"* — it should call `browse_catalog` and return your document list.
