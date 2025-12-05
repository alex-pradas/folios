# compare_versions

Generates a diff between two versions of a document.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | The document ID |
| `old_version` | integer | Yes | The older version |
| `new_version` | integer | Yes | The newer version |
| `format` | string | No | `"unified"`, `"summary"`, or `"both"` (default: `"both"`) |

## Response

### Default (both)

```json
{
  "result": {
    "unified_diff": "--- old\n+++ new\n@@ -15,6 +15,10 @@\n ## Static Analysis\n...",
    "summary": "4 lines added, 0 lines removed"
  }
}
```

### Unified diff only

With `format="unified"`:

```json
{
  "result": {
    "unified_diff": "--- old\n+++ new\n@@ -15,6 +15,10 @@\n ## Static Analysis\n...",
    "summary": null
  }
}
```

### Summary only

With `format="summary"`:

```json
{
  "result": {
    "unified_diff": "",
    "summary": "45 lines added, 12 lines removed"
  }
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
- Comparing identical versions returns an empty diff
- Works in either direction (can compare newer to older)
