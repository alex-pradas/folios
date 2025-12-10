# API Reference

MCP tools exposed by Folios for AI agents.

## get_document_content

Retrieve the full content of a document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `version` | integer | No | Specific version (default: latest) |

**Request:**

```json
{
  "tool": "get_document_content",
  "parameters": {"document_id": 123456}
}
```

**Response:**

```json
{
  "content": "---\ndocument_type: \"Design Practice\"\nauthor: \"J. Smith\"\ndate: \"2025-02-15\"\nstatus: \"Approved\"\n---\n\n# Stress Analysis Design Practice\n\n..."
}
```

---

## get_document_metadata

Retrieve metadata including title, author, status, and chapters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `version` | integer | No | Specific version (default: latest) |

**Request:**

```json
{
  "tool": "get_document_metadata",
  "parameters": {"document_id": 123456}
}
```

**Response:**

```json
{
  "metadata": {
    "id": 123456,
    "version": 2,
    "title": "Stress Analysis Design Practice",
    "author": "J. Smith",
    "date": "2025-02-15",
    "chapters": [
      {"title": "Purpose"},
      {"title": "Scope"},
      {"title": "Static Analysis"},
      {"title": "Fatigue Analysis"},
      {"title": "Thermal Analysis"}
    ],
    "document_type": "Design Practice",
    "reviewer": "A. Johnson",
    "approver": "M. Williams",
    "status": "Approved"
  }
}
```

---

## get_chapter_content

Retrieve the content of a specific chapter (H2 section) from a document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `chapter_title` | string | Yes | Title of the chapter to retrieve (case-insensitive) |
| `version` | integer | No | Specific version (default: latest) |

**Request:**

```json
{
  "tool": "get_chapter_content",
  "parameters": {"document_id": 123456, "chapter_title": "Static Analysis"}
}
```

**Response:**

```json
{
  "content": "## Static Analysis\n\nThis section covers static stress analysis methods...",
  "chapter_title": "Static Analysis"
}
```

!!! tip "Case-insensitive matching"
    The `chapter_title` parameter is case-insensitive. The response confirms which chapter was actually matched.

---

## diff_document_versions

Generate a diff between two versions, grouped by chapter. Only chapters with changes are included in the response.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `from_version` | integer | Yes | Older version to compare from |
| `to_version` | integer | Yes | Newer version to compare to |

**Request:**

```json
{
  "tool": "diff_document_versions",
  "parameters": {
    "document_id": 123456,
    "from_version": 1,
    "to_version": 2
  }
}
```

**Response:**

```json
{
  "changes": [
    {
      "chapter": "Metadata",
      "diff": "--- 123456_v1.md\n+++ 123456_v2.md\n@@ -1,5 +1,5 @@\n-date: \"2025-01-10\"\n+date: \"2025-02-15\""
    },
    {
      "chapter": "Methodology",
      "diff": "--- 123456_v1.md\n+++ 123456_v2.md\n@@ -1,3 +1,5 @@\n ## Methodology\n+\n+Added new content."
    }
  ]
}
```

**Notes:**

- `"Metadata"` covers YAML metadata, title, and any content before the first H2 heading
- Chapters with no changes are omitted from the response
- If there are no changes, returns `{"changes": []}`
- Chapter renames appear as two entries: the old name (with deletions) and new name (with additions)

---

## browse_catalog

List all documents with optional filtering. Filter values are discovered automatically from your documents at startup.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status |
| `document_type` | string | No | Filter by document type |
| `author` | string | No | Filter by author (case-insensitive substring) |

**Request:**

```json
{
  "tool": "browse_catalog",
  "parameters": {"status": "Approved"}
}
```

**Response:**

```json
[
  {
    "id": 123456,
    "title": "Introduction",
    "latest_version": 2,
    "status": "Approved",
    "document_type": "Design Practice"
  }
]
```

---

## list_revisions

List all available versions of a document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |

**Request:**

```json
{
  "tool": "list_revisions",
  "parameters": {"document_id": 123456}
}
```

**Response:**

```json
{
  "versions": [
    {"version": 1, "date": "2025-01-10", "status": "Approved", "author": "J. Smith"},
    {"version": 2, "date": "2025-02-15", "status": "Approved", "author": "J. Smith"}
  ]
}
```

---

## Error Codes

All tools return errors in the format `{"error": {"code": "...", "message": "..."}}`.

| Code | Description |
|------|-------------|
| `NOT_FOUND` | Document or version does not exist |
| `CHAPTER_NOT_FOUND` | Specified chapter does not exist in the document |
| `INVALID_FORMAT` | Document has malformed metadata or missing title |
| `READ_ERROR` | File system error (permissions, encoding, etc.) |

**Example:**

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Document 999999 not found"
  }
}
```

---

## MCP Resources

Folios also exposes documents as MCP resources, allowing clients to browse and access documents directly via URI.

### Resource URI Format

```
folios://documents/{document_id}/v{version}
```

### Resource Metadata

Each resource includes:
- **name**: Document title with version (e.g., "Stress Analysis Design Practice (v2)")
- **description**: Author, status, and document type
- **mime_type**: `text/markdown`

### Example

A document `123456_v2.md` with title "Stress Analysis" becomes:

```
URI: folios://documents/123456/v2
Name: Stress Analysis (v2)
Description: Author: J. Smith | Status: Approved | Type: Design Practice
```

### Usage

MCP clients can:
1. List all resources to see available documents
2. Read a resource by URI to get the full document content

!!! note
    Resources are registered at server startup. Adding new documents requires restarting the server.
