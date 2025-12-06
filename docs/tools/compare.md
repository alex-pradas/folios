# compare_versions

Generates a unified diff between two versions of a document.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | The document ID |
| `old_version` | integer | Yes | The older version |
| `new_version` | integer | Yes | The newer version |

## Response

### Success

```json
{
  "diff": "--- 123456_v1.md\n+++ 123456_v2.md\n@@ -1,12 +1,12 @@\n..."
}
```

### No changes

When versions are identical:

```json
{
  "diff": "No changes between versions."
}
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

## Notes

- Uses Python's `difflib` unified diff format
- Comparing identical versions returns "No changes between versions."
- Works in either direction (can compare newer to older)
