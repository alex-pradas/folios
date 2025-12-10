# Troubleshooting

Common issues and how to resolve them.

## Server Issues

### Server won't start

**Symptom:** Error when running `uvx folios --path /path/to/docs`

**Possible causes:**

1. **Invalid path** - The documents folder doesn't exist
   ```
   Error: Documents path does not exist: /path/to/docs
   ```
   **Solution:** Check the path exists and is accessible.

2. **Port already in use** - Another process is using the MCP socket
   **Solution:** Check for other Folios instances or MCP servers running.

### Documents not appearing

**Symptom:** `browse_catalog` returns empty list but documents exist in the folder.

**Possible causes:**

1. **Wrong filename pattern** - Files must match `{id}_v{version}.md`
   ```
   # These won't work:
   my-document.md
   doc_v1.txt
   123456.md

   # These will work:
   123456_v1.md
   1_v1.md
   999999_v42.md
   ```

2. **Missing H1 title** - Every document needs a `# Title` heading
   ```markdown
   # This Document Has a Title

   Content here...
   ```

3. **Server needs restart** - Schema discovery only happens at startup
   **Solution:** Restart the server after adding new documents.

### New documents not showing up

**Symptom:** Added a new document but it doesn't appear in `browse_catalog`.

**Cause:** Schema discovery happens once at startup.

**Solution:** Restart the Folios server to pick up new documents.

## Tool Errors

### NOT_FOUND error

```json
{"error": {"code": "NOT_FOUND", "message": "Document 123456 not found"}}
```

**Possible causes:**

- Document ID doesn't exist
- Requested version doesn't exist (e.g., asking for v3 when only v1 and v2 exist)

**Solution:** Use `browse_catalog` to see available documents, then `list_revisions` to see available versions.

### CHAPTER_NOT_FOUND error

```json
{"error": {"code": "CHAPTER_NOT_FOUND", "message": "Chapter 'Introduction' not found"}}
```

**Cause:** The requested chapter title doesn't match any H2 heading in the document.

**Solution:** Use `get_document_metadata` first to see available chapters:

```json
{
  "chapters": [
    {"title": "Background"},
    {"title": "Methodology"}
  ]
}
```

!!! tip
    Chapter matching is case-insensitive, so "background" will match "Background".

### INVALID_FORMAT error

```json
{"error": {"code": "INVALID_FORMAT", "message": "Missing document title"}}
```

**Possible causes:**

1. **No H1 heading** - Document is missing the `# Title` line
2. **Malformed YAML** - Metadata block has syntax errors

**Example of malformed YAML:**

```markdown
---
status: "Draft
author: Missing closing quote
---
```

**Solution:** Check the document has a valid H1 title and properly formatted YAML metadata.

### READ_ERROR

```json
{"error": {"code": "READ_ERROR", "message": "Permission denied"}}
```

**Cause:** File system issue - permissions, file moved, encoding problems.

**Solution:** Check file permissions and ensure the file exists and is readable.

## MCP Client Issues

### Tools not showing in Claude Desktop

**Symptom:** Folios tools don't appear in Claude Desktop's tool list.

**Possible causes:**

1. **Configuration error** - Check `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "folios": {
         "command": "uvx",
         "args": ["folios", "--path", "/path/to/documents"]
       }
     }
   }
   ```

2. **uvx not found** - Ensure `uv` is installed and in your PATH

3. **Server crash** - Check logs for errors:
   ```json
   {
     "mcpServers": {
       "folios": {
         "command": "uvx",
         "args": ["folios", "--path", "/path/to/documents"],
         "env": {
           "FASTMCP_LOG_LEVEL": "DEBUG"
         }
       }
     }
   }
   ```

### Filter values not appearing

**Symptom:** The `browse_catalog` tool description doesn't show filter hints.

**Cause:** No documents with metadata, or all fields have >15 unique values.

**Solution:** Check that documents have YAML metadata blocks with fields like `status`, `document_type`, etc.

## Performance Issues

### Slow startup with many documents

**Symptom:** Server takes a long time to start.

Schema discovery is very fast (~70K docs/sec), so this is unlikely unless you have hundreds of thousands of documents.

**Solution:** Check for:

- Network drive latency
- Very large individual documents
- Disk I/O issues

### High memory usage

**Symptom:** Server uses excessive memory.

Folios loads document content on-demand, not at startup. High memory usage suggests either:

- Very large documents being read repeatedly
- Many concurrent requests

## Getting Help

If you're still stuck:

1. Check the [GitHub issues](https://github.com/alex-pradas/folios/issues)
2. Enable debug logging to see detailed output
3. Open a new issue with reproduction steps
