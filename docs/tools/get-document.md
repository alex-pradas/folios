# get_document_content

Retrieves the raw content of a document, including YAML frontmatter.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier of the document |
| `version` | integer | No | Specific version (defaults to latest) |

## Response

Returns the full document content as a string:

```markdown
---
type: Design Practice
author: John Smith
reviewer: Jane Doe
approver: Bob Wilson
date: 2025-02-15
status: Approved
---

# Stress Analysis Design Practice

This document describes the stress analysis methodology...

## Scope

Applicable to all load-bearing structures.
```

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

**Version not found:**

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Document 123456 version 3 not found"
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

- Returns raw content even if the document has malformed metadata
- Use `get_document_metadata` if you need structured metadata
- Gracefully handles remote drive errors (network issues, permission changes)
