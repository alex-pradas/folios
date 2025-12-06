# Tools Reference

Folios provides 5 MCP tools for document management. Your AI assistant will use these tools automatically based on your requests.

For auto-generated documentation from source code, see the [API Reference](../api-reference.md).

## Available Tools

| Tool | Purpose |
|------|---------|
| [`get_document_content`](get-document.md) | Retrieve raw document content |
| [`get_document_metadata`](get-metadata.md) | Get structured metadata and chapters |
| [`list_documents`](list-documents.md) | Browse and filter documents |
| [`list_document_versions`](list-versions.md) | View version history for a document |
| [`diff_document_versions`](compare.md) | Generate diffs between versions |

## How It Works

When you ask your AI assistant something like:

> "Show me document 100001"

The assistant calls `get_document_content` with `document_id=100001` and returns the content.

> "What documents are approved?"

The assistant calls `list_documents` with `status="Approved"` and shows the results.

> "What changed in the latest version?"

The assistant calls `list_document_versions` to find versions, then `diff_document_versions` to show the diff.

## Error Handling

All tools return structured errors when something goes wrong:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Document 123456 not found"
  }
}
```

**Error codes:**

| Code | Meaning |
|------|---------|
| `NOT_FOUND` | Document or version doesn't exist |
| `INVALID_FORMAT` | Document has malformed structure |
| `READ_ERROR` | I/O error reading file (permission denied, network error, etc.) |
