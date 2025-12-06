# API Reference

MCP tools exposed by Folios for AI agents.

## get_document_content

Retrieve the full content of a document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `version` | integer | No | Specific version (default: latest) |

=== "Request"
    ```json
    {
      "tool": "get_document_content",
      "parameters": {"document_id": 123456}
    }
    ```

=== "Response"
    ```json
    {
      "content": "---\ndocument_type: Design Practice\nauthor: J. Smith\nstatus: Approved\n---\n\n# Stress Analysis\n\n## Scope\n\nThis document covers..."
    }
    ```

---

## get_document_metadata

Retrieve metadata including title, author, status, and chapters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `version` | integer | No | Specific version (default: latest) |

=== "Request"
    ```json
    {
      "tool": "get_document_metadata",
      "parameters": {"document_id": 123456}
    }
    ```

=== "Response"
    ```json
    {
      "metadata": {
        "id": 123456,
        "version": 2,
        "title": "Stress Analysis Design Practice",
        "author": "J. Smith",
        "date": "2025-02-15",
        "document_type": "Design Practice",
        "status": "Approved",
        "reviewer": "A. Johnson",
        "chapters": [
          {"title": "Scope"},
          {"title": "Methodology"},
          {"title": "References"}
        ]
      }
    }
    ```

---

## diff_document_versions

Generate a unified diff between two versions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |
| `from_version` | integer | Yes | Older version to compare from |
| `to_version` | integer | Yes | Newer version to compare to |

=== "Request"
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

=== "Response"
    ```json
    {
      "diff": "--- 123456_v1.md\n+++ 123456_v2.md\n@@ -3,7 +3,7 @@\n author: J. Smith\n-status: Draft\n+status: Approved\n---"
    }
    ```

---

## list_documents

List all documents with optional filtering. Filter values are discovered automatically from your documents at startup.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status |
| `document_type` | string | No | Filter by document type |
| `author` | string | No | Filter by author (case-insensitive substring) |

=== "Request"
    ```json
    {
      "tool": "list_documents",
      "parameters": {"status": "Approved"}
    }
    ```

=== "Response"
    ```json
    [
      {
        "id": 123456,
        "title": "Stress Analysis",
        "latest_version": 2,
        "status": "Approved",
        "document_type": "Design Practice"
      },
      {
        "id": 789012,
        "title": "Fatigue Analysis",
        "latest_version": 1,
        "status": "Approved",
        "document_type": "Design Practice"
      }
    ]
    ```

---

## list_document_versions

List all available versions of a document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | integer | Yes | Unique numeric identifier |

=== "Request"
    ```json
    {
      "tool": "list_document_versions",
      "parameters": {"document_id": 123456}
    }
    ```

=== "Response"
    ```json
    {
      "versions": [
        {"version": 1, "date": "2025-01-10", "status": "Draft", "author": "J. Smith"},
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
| `INVALID_FORMAT` | Document has malformed frontmatter or missing title |
| `READ_ERROR` | File system error (permissions, encoding, etc.) |

=== "Error Example"
    ```json
    {
      "error": {
        "code": "NOT_FOUND",
        "message": "Document 999999 not found"
      }
    }
    ```

