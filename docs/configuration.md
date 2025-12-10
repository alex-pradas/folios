# Configuration

Folios works out of the box with zero configuration. Just point it at a folder of Markdown files and it automatically discovers field values from your documents.

## Automatic Schema Discovery

When Folios starts, it scans all documents in your folder and discovers the unique values for each metadata field. This information is then included in the MCP tool descriptions so AI agents know exactly what filter values are available.

### How It Works

1. **At startup**, Folios reads all `.md` files matching the `{id}_v{version}.md` pattern
2. **Extracts metadata** from each document
3. **Collects unique values** for each field across all documents
4. **Classifies fields** as enumerable (≤15 unique values) or free-text (>15 values)
5. **Includes hints** in the `browse_catalog` tool description for the Agent to know

### Example

Given these documents:

```markdown
<!-- 100001_v1.md -->
---
status: "Draft"
document_type: "Guideline"
author: "Alice"
---

<!-- 100002_v1.md -->
---
status: "Approved"
document_type: "TRS"
author: "Bob"
---

<!-- 100003_v1.md -->
---
status: "Draft"
document_type: "Design Practice"
author: "Alice"
---
```

Folios will discover:

- **status**: Draft, Approved (2 values - enumerable)
- **document_type**: Design Practice, Guideline, TRS (3 values - enumerable)
- **author**: Alice, Bob (2 values - enumerable)

The `browse_catalog` tool description will include:

```
Discovered filters:
  author: Alice, Bob
  document_type: Design Practice, Guideline, TRS
  status: Approved, Draft
```

### Field Classification

Fields are classified based on the number of unique values:

| Unique Values | Classification | Display |
|---------------|----------------|---------|
| ≤15 | Enumerable | All values listed |
| >15 | Free-text | Shows count only |

For example, if you have 50 different authors, the hints would show:

```
Discovered filters:
  author: free text (50 unique values)
  status: Approved, Draft
```

This prevents overwhelming the AI agent with too many options while still indicating the field is filterable.

## Benefits

- **Zero configuration required** - no separate config file to maintain
- **Always up-to-date** - schema reflects actual document content
- **No drift** - impossible for config to get out of sync with documents
- **Automatic** - just add documents and the schema updates on restart

## Performance

Schema discovery is extremely fast:

- ~15ms for 1000 documents
- ~70,000 documents per second

This happens once at server startup and has negligible impact on launch time.

## Logging

Folios logs server activity to stderr, useful for debugging and monitoring performance.

### Example Output

```
[12/10/25 21:46:48] INFO     Folios v0.7.2 starting
                    INFO     Documents path: /path/to/docs
                    INFO     Scanned 42 documents
                    INFO     Schema discovery: 5 fields in 234.5ms
                    INFO     Server ready

                    INFO     browse_catalog(status=None, document_type=None, author=None)
                    DEBUG    Returned 42 documents in 45.2ms
```

### Log Levels

Control verbosity via the `FASTMCP_LOG_LEVEL` environment variable:

| Level | Shows |
|-------|-------|
| `DEBUG` | Per-file parsing times, response sizes, detailed timing |
| `INFO` (default) | Tool invocations, startup info, document counts |
| `WARNING` | Warnings and errors only |
| `ERROR` | Errors only |

### Usage

```bash
# Verbose output (shows per-file parsing)
FASTMCP_LOG_LEVEL=DEBUG uvx folios --path /path/to/docs

# Quiet mode
FASTMCP_LOG_LEVEL=WARNING uvx folios --path /path/to/docs
```

In Claude Desktop configuration:

```json
{
  "mcpServers": {
    "folios": {
      "command": "uvx",
      "args": ["folios", "--path", "/path/to/documents"],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

!!! note
    Logs go to stderr, so they won't interfere with the MCP protocol on stdout. In Claude Desktop, logs are captured but not displayed to the user.

!!! warning "Restart required for new documents"
    Schema discovery happens at server startup only. Adding new documents requires restarting the server to pick up changes.

## Notes

- Documents with parsing errors are skipped gracefully
- Non-string values are converted to strings for filtering
