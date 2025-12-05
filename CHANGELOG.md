# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-06

### Added
- Initial release (renamed from alexandria-mcp to folios)
- Document storage with versioning support (`{id}_v{version}.md` naming)
- YAML frontmatter parsing for metadata (author, reviewer, approver, status, type)
- Auto-parsed chapters from H1/H2 headings
- MCP tools:
  - `get_document` - Retrieve document content
  - `get_document_metadata` - Get metadata including chapters
  - `compare_versions` - Generate diffs between versions
  - `list_documents` - List documents with filters
  - `list_versions` - List all versions of a document
- FastMCP-based server implementation
- Comprehensive test suite
