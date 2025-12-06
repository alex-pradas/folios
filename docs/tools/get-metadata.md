# get_document_metadata

Retrieves structured metadata for a document, including auto-parsed chapters from headings.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier of the document |
| `version` | integer | No | Specific version (defaults to latest) |

## Response

Returns structured metadata:

```json
{
  "metadata": {
    "id": 123456,
    "version": 2,
    "title": "Stress Analysis Design Practice",
    "type": "Design Practice",
    "author": "John Smith",
    "reviewer": "Jane Doe",
    "approver": "Bob Wilson",
    "date": "2025-02-15",
    "status": "Approved",
    "chapters": [
      {"title": "Scope"},
      {"title": "Methodology"},
      {"title": "Static Analysis"},
      {"title": "Dynamic Analysis"}
    ]
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `id` | Document ID (from filename) |
| `version` | Version number (from filename) |
| `title` | Document title (from H1 heading) |
| `type` | Document type |
| `author` | Document author |
| `reviewer` | Document reviewer |
| `approver` | Document approver |
| `date` | Publication date |
| `status` | Document status |
| `chapters` | Auto-parsed from H2 headings |

## Errors

**Document not found:**

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Document 123456 not found"
  }
}
```

**Invalid format:**

```json
{
  "error": {
    "code": "INVALID_FORMAT",
    "message": "Document missing title (H1 heading)"
  }
}
```

**Read error (permission denied, network error, etc.):**

```json
{
  "error": {
    "code": "READ_ERROR",
    "message": "[EACCES] Permission denied (file: /path/to/document.md)"
  }
}
```

## Notes

- Validates document structure (unlike `get_document_content`)
- Missing optional fields show as "NA"
- Chapters are extracted from `##` headings only
- Gracefully handles remote drive errors (network issues, permission changes)
