# Configuration

Folios works out of the box with zero configuration. Just point it at a folder of Markdown files and it automatically discovers field values from your documents.

## Automatic Schema Discovery

When Folios starts, it scans all documents in your folder and discovers the unique values for each frontmatter field. This information is then included in the MCP tool descriptions so AI agents know exactly what filter values are available.

### How It Works

1. **At startup**, Folios reads all `.md` files matching the `{id}_v{version}.md` pattern
2. **Extracts frontmatter** from each document
3. **Collects unique values** for each field across all documents
4. **Classifies fields** as enumerable (≤15 unique values) or free-text (>15 values)
5. **Includes hints** in the `list_documents` tool description

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

The `list_documents` tool description will include:

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

## Notes

- Discovery happens at server startup only
- Adding new documents requires restarting the server to update the schema
- Documents with parsing errors are skipped gracefully
- Non-string values are converted to strings for filtering
