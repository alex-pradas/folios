# list_documents

Lists documents in the library with optional filtering.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status |
| `document_type` | string | No | Filter by document type |
| `author` | string | No | Filter by author (case-insensitive, partial match) |

## Response

Returns an array of document summaries:

```json
[
  {
    "id": 123456,
    "title": "Stress Analysis Design Practice",
    "latest_version": 2,
    "status": "Approved",
    "type": "Design Practice"
  },
  {
    "id": 123457,
    "title": "Material Selection Guidelines",
    "latest_version": 1,
    "status": "In Review",
    "type": "Guideline"
  }
]
```

### Fields

| Field | Description |
|-------|-------------|
| `id` | Document ID |
| `title` | Document title |
| `latest_version` | Most recent version number |
| `status` | Document status |
| `type` | Document type |

## Filter Values

### Status

- `Draft`
- `In Review`
- `Approved`
- `Withdrawn`

### Type

- `Design Practice`
- `Guideline`
- `Best Practice`
- `TRS`
- `DVP`
- `DVR`

## Notes

- Filters combine with AND logic (all must match)
- Author filter is case-insensitive and matches partial names
- Returns empty array if no matches (not an error)
- Malformed documents are skipped
- Shows only the latest version's metadata
