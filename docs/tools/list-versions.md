# list_versions

Shows all versions of a document with their metadata.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | The document ID |

## Response

Returns version history:

```json
{
  "versions": [
    {
      "version": 1,
      "date": "2025-01-10",
      "status": "Withdrawn",
      "author": "John Smith"
    },
    {
      "version": 2,
      "date": "2025-02-15",
      "status": "Approved",
      "author": "John Smith"
    }
  ]
}
```

### Fields

| Field | Description |
|-------|-------------|
| `version` | Version number |
| `date` | Publication date |
| `status` | Document status at this version |
| `author` | Document author at this version |

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

## Notes

- Versions are sorted in ascending order (oldest first)
- Malformed versions are skipped
- Use `compare_versions` to see what changed between versions
