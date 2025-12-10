# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] - 2025-12-10

### Changed

- Clarified documentation

## [0.7.0] - 2025-12-10

### Changed

- **BREAKING**: Renamed `list_documents` tool to `browse_catalog`
- **BREAKING**: Renamed `list_document_versions` tool to `list_revisions`

### Added

- MCP Resources documentation in API reference
- Limitations section in README
- Features list now includes chapter extraction, version diffing, and MCP resources

## [0.6.0] - 2025-12-10

### Added

- New `get_chapter_content` tool to retrieve specific H2 sections from documents
- Chapter-grouped diffs in `diff_document_versions` - changes now organized by chapter name
- `CHAPTER_NOT_FOUND` error code for invalid chapter requests

### Changed

- `diff_document_versions` response format now returns `{"changes": [{"chapter": "...", "diff": "..."}]}` instead of a single unified diff

### Fixed

- Documentation accuracy improvements across README and docs

## [0.5.0] - 2025-12-09

### Changed

- **BREAKING**: Renamed CLI flag `--folios-path` to `--path` (environment variable `FOLIOS_PATH` unchanged)

### Added

- Logo and example screenshot in README and documentation

## [0.4.1] - 2025-12-06

### Fixed

- Use explicit `AnyUrl` type for resource URIs to satisfy type checker

## [0.4.0] - 2025-12-06

### Added

- MCP resources for document access via `folios://documents/{id}/v{version}` URIs
- Resource listing includes document metadata (title, author, status, type)
- Lazy content loading - documents read on access, not at startup

## [0.3.0] - 2025-12-06

### Added

- Server logging with timing information for debugging and monitoring
- Log tool invocations with parameters at INFO level
- Log response times and sizes at DEBUG level
- Log schema discovery and per-file parsing performance
- Documentation for logging configuration in docs/configuration.md

### Changed

- Uses FastMCP's `get_logger` for consistent log formatting

## [0.2.0] - 2025-12-06

### Added

- Automatic schema discovery from documents at startup
- Smart field classification (enumerable ≤15 values vs free-text >15 values)
- Filter hints in `list_documents` tool description showing available values

### Changed

- Server now uses factory pattern (`create_server()`) for better testability
- Documents path passed explicitly instead of global state

### Removed

- **BREAKING**: `folios.toml` configuration file support removed
- Manual field value configuration no longer needed

### Performance

- Schema discovery: ~15ms for 1000 documents (~70K docs/sec)

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
