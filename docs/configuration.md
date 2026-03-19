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
[03/19/26 15:46:11] INFO     Folios v0.10.0 starting
                    INFO     Documents path: /path/to/docs
                    INFO     Scanned 42 documents
                    INFO     Schema discovery: 5 fields in 0.6ms
                    INFO     Registered 42 document resources
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

## Images

Documents can reference images (diagrams, charts, photos) that are served as separate MCP resources. Agents can fetch individual images on demand to reason about visual content.

### Folder Convention

Place images in a `{id}_images/` folder alongside your document files:

```
documents/
├── 123456_v1.md
├── 123456_v2.md
├── 123456_images/
│   ├── diagram.png
│   └── photo.jpg
├── 789012_v1.md
└── 789012_images/
    └── flowchart.png
```

The image folder is shared across all versions of the same document.

### Referencing Images

In your markdown documents, reference images with relative paths:

```markdown
![System diagram](123456_images/diagram.png)
```

### MCP Resources

Each image is registered as a binary MCP resource at:

```
folios://images/{doc_id}/{filename}
```

For example, `123456_images/diagram.png` becomes `folios://images/123456/diagram.png`.

Agents can read these resources to view the actual image content.

### Supported Formats

| Extension | MIME Type |
|-----------|-----------|
| `.png` | image/png |
| `.jpg`, `.jpeg` | image/jpeg |
| `.gif` | image/gif |
| `.svg` | image/svg+xml |
| `.webp` | image/webp |

!!! note
    Image resources are registered at startup. Add images and restart the server to pick up changes.

## Custom MCP Resources

You can expose additional markdown files as MCP resources by placing them in a `.mcp_resources/` subfolder inside your documents directory. This is useful for workflow guides, templates, conventions, or any structured guidance that agents should have access to.

### Setup

```
documents/
├── 100001_v1.md
├── 100002_v1.md
└── .mcp_resources/
    ├── how-to-propose-changes.md
    └── review-checklist.md
```

Each `.md` file in `.mcp_resources/` is registered as an MCP resource at:

```
folios://{filename-without-extension}
```

For example, `how-to-propose-changes.md` becomes `folios://how-to-propose-changes`.

### Resource naming

- **Name**: extracted from the first `# H1` heading in the file, or the filename if no heading is found
- **Description**: extracted from the first paragraph of content
- **Content**: served as raw markdown

### Use cases

- **Workflow guides** — "How to propose a document change"
- **Templates** — standard document structures for agents to follow
- **Conventions** — naming rules, formatting standards, review criteria
- **Instructions** — agent-specific guidance for working with your documents

!!! note
    Custom resources are registered at startup. Add or update files in `.mcp_resources/` and restart the server to pick up changes.

## Notes

- Documents with parsing errors are skipped gracefully
- Non-string values are converted to strings for filtering
