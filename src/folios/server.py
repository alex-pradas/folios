"""Folios MCP Server.

FastMCP server providing versioned document retrieval, metadata access,
and diff capabilities for engineering documents.
"""

import argparse
import difflib
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any
from importlib.metadata import version

from fastmcp import FastMCP
from pydantic import BaseModel

# Module-level variable for CLI-specified path (set by main())
_cli_folios_path: Path | None = None

# Module-level cache for configuration
_config_cache: dict | None = None
_config_loaded: bool = False

# =============================================================================
# Pydantic Models
# =============================================================================


class Chapter(BaseModel):
    """Represents a document section heading (H2)."""

    title: str  # Heading text


class DocumentSummary(BaseModel):
    """Summary for list_documents results."""

    id: int
    title: str = "NA"
    latest_version: int
    status: str = "NA"
    document_type: str = "NA"


class VersionInfo(BaseModel):
    """Version information for list_versions results."""

    version: int
    date: str = "NA"
    status: str = "NA"
    author: str = "NA"


class ErrorResponse(BaseModel):
    """Structured error for graceful failure responses."""

    code: str  # "NOT_FOUND", "INVALID_FORMAT", "MISSING_FIELD", "READ_ERROR"
    message: str


def format_os_error(error: OSError) -> str:
    """Format an OSError into a human-readable message.

    Args:
        error: The OSError (or subclass) to format.

    Returns:
        Human-readable error message with context.
    """
    # Get the error name from errno if available
    error_name = ""
    if error.errno is not None:
        import errno as errno_module
        error_name = errno_module.errorcode.get(error.errno, "")

    # Build informative message
    parts = []
    if error_name:
        parts.append(f"[{error_name}]")
    if error.strerror:
        parts.append(error.strerror)
    elif str(error):
        parts.append(str(error))
    if error.filename:
        parts.append(f"(file: {error.filename})")

    return " ".join(parts) if parts else "Unknown I/O error"


# =============================================================================
# Configuration
# =============================================================================


def get_documents_path() -> Path:
    """Get the documents path from CLI flag or environment variable.

    Priority:
    1. --folios-path CLI flag
    2. FOLIOS_PATH environment variable

    Raises:
        RuntimeError: If no path is configured.
    """
    if _cli_folios_path is not None:
        return _cli_folios_path
    env_path = os.environ.get("FOLIOS_PATH")
    if env_path:
        return Path(env_path)
    raise RuntimeError("No documents path configured")


def load_config() -> dict[str, Any] | None:
    """Load configuration from folios.toml in the documents folder.

    Returns:
        Configuration dict if folios.toml exists, None otherwise.
        Returns cached config on subsequent calls.
    """
    global _config_cache, _config_loaded

    if _config_loaded:
        return _config_cache

    _config_loaded = True

    try:
        config_path = get_documents_path() / "folios.toml"
        if config_path.exists():
            with open(config_path, "rb") as f:
                _config_cache = tomllib.load(f)
            return _config_cache
    except (RuntimeError, OSError):
        # No documents path configured or can't read config
        pass

    return None


def get_field_values(field_name: str) -> list[str] | None:
    """Get allowed values for a field from configuration.

    Args:
        field_name: The field name to look up (e.g., 'status', 'document_type').

    Returns:
        List of allowed values if configured, None otherwise.
    """
    config = load_config()
    if config and "fields" in config:
        field_config = config["fields"].get(field_name, {})
        return field_config.get("values")
    return None


def reset_config_cache() -> None:
    """Reset the configuration cache. Useful for testing."""
    global _config_cache, _config_loaded
    _config_cache = None
    _config_loaded = False


# Pattern for parsing document filenames: {id}_v{version}.md
FILENAME_PATTERN = re.compile(r"^(\d+)_v(\d+)\.md$")

# Pattern for extracting title (first H1 heading)
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Pattern for parsing H2 headings (chapters)
HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# =============================================================================
# Storage Functions
# =============================================================================


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from document content.

    Args:
        content: Full document content with frontmatter.

    Returns:
        Tuple of (frontmatter dict, body content).

    Raises:
        ValueError: If frontmatter delimiters are malformed (started but not closed).
    """
    # No frontmatter - return empty dict and full content as body
    if not content.startswith("---"):
        return {}, content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid frontmatter format: missing closing delimiter")

    frontmatter_text = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML parser for key: value pairs
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Remove surrounding quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        # Convert to int if numeric
        if value.isdigit():
            frontmatter[key] = int(value)
        else:
            frontmatter[key] = value

    return frontmatter, body


def parse_title(content: str) -> str:
    """Extract title from first H1 heading.

    Args:
        content: Document body content (without frontmatter).

    Returns:
        Title string from first H1 heading.

    Raises:
        ValueError: If no H1 heading is found.
    """
    match = TITLE_PATTERN.search(content)
    if not match:
        raise ValueError("Document missing title (H1 heading)")
    return match.group(1).strip()


def parse_chapters(content: str) -> list[Chapter]:
    """Extract H2 headings from document content as chapters.

    Args:
        content: Document body content (without frontmatter).

    Returns:
        List of Chapter objects with title.
    """
    chapters = []
    for match in HEADING_PATTERN.finditer(content):
        title = match.group(1).strip()
        chapters.append(Chapter(title=title))
    return chapters


def parse_document(path: Path, doc_id: int, doc_version: int) -> tuple[dict[str, Any], str]:
    """Parse a document file into metadata and content.

    The id and version are derived from the filename, and title is extracted
    from the first H1 heading in the document body.

    Args:
        path: Path to the markdown document file.
        doc_id: Document ID (from filename).
        doc_version: Document version (from filename).

    Returns:
        Tuple of (metadata dict, body content).
        Metadata always includes: id, version, title, author, date, chapters.
        Additional frontmatter fields are included dynamically.

    Raises:
        FileNotFoundError: If document file doesn't exist.
        ValueError: If document format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    title = parse_title(body)
    chapters = parse_chapters(body)

    # Build metadata dict with core fields first
    metadata: dict[str, Any] = {
        "id": doc_id,
        "version": doc_version,
        "title": title,
        "author": frontmatter.get("author", "NA"),
        "date": frontmatter.get("date", "NA"),
        "chapters": [{"title": ch.title} for ch in chapters],
    }

    # Add all other frontmatter fields dynamically
    for key, value in frontmatter.items():
        if key not in ("author", "date"):  # Already handled above
            metadata[key] = value

    return metadata, body


def get_all_document_files() -> list[tuple[int, int, Path]]:
    """Scan documents directory and return all document files.

    Returns:
        List of tuples (doc_id, version, path) for each document file.
        Returns empty list if directory is inaccessible.
    """
    try:
        documents_path = get_documents_path()
        if not documents_path.exists():
            return []
    except OSError:
        # Directory existence check failed (network issue, permission, etc.)
        return []

    documents = []
    try:
        for path in documents_path.glob("*.md"):
            try:
                # Verify the path is a file (not a directory with .md extension)
                if not path.is_file():
                    continue
                match = FILENAME_PATTERN.match(path.name)
                if match:
                    doc_id = int(match.group(1))
                    version = int(match.group(2))
                    documents.append((doc_id, version, path))
            except OSError:
                # Skip files that can't be accessed
                continue
    except OSError:
        # Directory listing failed (network issue, permission, etc.)
        return []

    return documents


def get_latest_version(doc_id: int) -> int | None:
    """Find the highest version number for a document ID.

    Args:
        doc_id: The document ID to search for.

    Returns:
        Highest version number, or None if document not found.
    """
    versions = [v for d, v, _ in get_all_document_files() if d == doc_id]
    return max(versions) if versions else None


def find_document_path(doc_id: int, version: int | None = None) -> tuple[Path, int]:
    """Resolve the file path for a document.

    Args:
        doc_id: The document ID.
        version: Specific version, or None for latest.

    Returns:
        Tuple of (path to document file, resolved version number).

    Raises:
        FileNotFoundError: If document or version doesn't exist.
    """
    if version is None:
        version = get_latest_version(doc_id)
        if version is None:
            raise FileNotFoundError(f"Document {doc_id} not found")

    documents_path = get_documents_path()
    path = documents_path / f"{doc_id}_v{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Document {doc_id} version {version} not found")

    return path, version


def scan_documents(
    status: str | None = None,
    doc_type: str | None = None,
    author: str | None = None,
) -> list[DocumentSummary]:
    """Scan and filter documents, returning summaries.

    Args:
        status: Filter by document status.
        doc_type: Filter by document type.
        author: Filter by author name (case-insensitive substring match).

    Returns:
        List of DocumentSummary for matching documents.
    """
    # Group files by document ID
    doc_versions: dict[int, list[tuple[int, Path]]] = {}
    for doc_id, version, path in get_all_document_files():
        if doc_id not in doc_versions:
            doc_versions[doc_id] = []
        doc_versions[doc_id].append((version, path))

    summaries = []
    for doc_id, versions in doc_versions.items():
        # Get latest version
        latest_version, latest_path = max(versions, key=lambda x: x[0])

        try:
            content = latest_path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)
            doc_title = parse_title(body)
        except (ValueError, OSError):
            continue  # Skip files that can't be read or parsed

        # Extract fields with "NA" defaults for missing values
        doc_status = frontmatter.get("status", "NA")
        doc_type_val = frontmatter.get("document_type", "NA")
        doc_author = frontmatter.get("author", "NA")

        # Apply filters (skip filter if field is "NA")
        if status and doc_status != "NA" and doc_status != status:
            continue
        if doc_type and doc_type_val != "NA" and doc_type_val != doc_type:
            continue
        if author and doc_author != "NA" and author.lower() not in doc_author.lower():
            continue

        summaries.append(
            DocumentSummary(
                id=doc_id,
                title=doc_title,
                latest_version=latest_version,
                status=doc_status,
                document_type=doc_type_val,
            )
        )

    return summaries

# =============================================================================
# FastMCP Server
# =============================================================================

__version__ = version("folios")

server = FastMCP(
    name="folios",
    instructions="Retrieve and compare versioned engineering documents. "
    "Documents have metadata (author, status, document_type) and chapters extracted from headings. "
    "Set FOLIOS_PATH environment variable to configure the documents folder.",
    version=__version__,
)


@server.tool
def get_document_content(document_id: int, version: int | None = None) -> dict:
    """Retrieve the full content of a document.

    Args:
        document_id: Unique numeric identifier of the document.
        version: Specific version number to retrieve. If not provided, returns the latest version.

    Returns:
        On success: {"content": "<full markdown content>"}
        On error: {"error": {"code": "NOT_FOUND"|"READ_ERROR", "message": "..."}}

    Example:
        Tool call:
        ```json
        {"tool": "get_document_content", "parameters": {"document_id": 123456}}
        ```

        Response:
        ```json
        {"content": "---\\ntype: Design Practice\\nauthor: J. Smith\\n..."}
        ```
    """
    try:
        path, _ = find_document_path(document_id, version)
        return {"content": path.read_text(encoding="utf-8")}
    except FileNotFoundError as e:
        return {"error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()}
    except UnicodeDecodeError as e:
        return {
            "error": ErrorResponse(
                code="READ_ERROR",
                message=f"File encoding error: {e.reason}"
            ).model_dump()
        }
    except MemoryError:
        return {
            "error": ErrorResponse(
                code="READ_ERROR",
                message="File too large to read into memory"
            ).model_dump()
        }
    except OSError as e:
        return {
            "error": ErrorResponse(
                code="READ_ERROR",
                message=format_os_error(e)
            ).model_dump()
        }


@server.tool
def get_document_metadata(document_id: int, version: int | None = None) -> dict:
    """Retrieve metadata for a document including title, author, and chapters.

    Args:
        document_id: Unique numeric identifier of the document.
        version: Specific version number. If not provided, returns metadata for the latest version.

    Returns:
        On success: {"metadata": {id, version, title, author, date, chapters, ...}}
            Core fields (id, version, title, author, date, chapters) are always present.
            Author and date show "NA" if not in frontmatter.
            Additional frontmatter fields are included dynamically.
        On error: {"error": {"code": "NOT_FOUND"|"INVALID_FORMAT"|"READ_ERROR", "message": "..."}}

    Example:
        Tool call:
        ```json
        {"tool": "get_document_metadata", "parameters": {"document_id": 123456}}
        ```

        Response:
        ```json
        {
          "metadata": {
            "id": 123456,
            "version": 2,
            "title": "Stress Analysis Design Practice",
            "author": "J. Smith",
            "date": "2025-02-15",
            "chapters": [{"title": "Scope"}, {"title": "Methodology"}],
            "document_type": "Design Practice",
            "status": "Approved",
            "reviewer": "A. Johnson"
          }
        }
        ```
    """
    try:
        path, resolved_version = find_document_path(document_id, version)
        metadata, _ = parse_document(path, document_id, resolved_version)
        return {"metadata": metadata}
    except FileNotFoundError as e:
        return {"error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()}
    except (ValueError, KeyError) as e:
        return {
            "error": ErrorResponse(code="INVALID_FORMAT", message=str(e)).model_dump()
        }
    except OSError as e:
        return {
            "error": ErrorResponse(
                code="READ_ERROR",
                message=format_os_error(e)
            ).model_dump()
        }


@server.tool
def diff_document_versions(
    document_id: int,
    from_version: int,
    to_version: int,
) -> dict:
    """Generate a unified diff between two versions of a document.

    Args:
        document_id: Unique numeric identifier of the document.
        from_version: The older version number to compare from.
        to_version: The newer version number to compare to.

    Returns:
        On success: {"diff": "<unified diff text>"}
        On no changes: {"diff": "No changes between versions."}
        On error: {"error": {"code": "NOT_FOUND"|"READ_ERROR", "message": "..."}}

    Example:
        Tool call:
        ```json
        {"tool": "diff_document_versions", "parameters": {"document_id": 123456, "from_version": 1, "to_version": 2}}
        ```

        Response:
        ```json
        {"diff": "--- 123456_v1.md\\n+++ 123456_v2.md\\n@@ -5,7 +5,7 @@\\n..."}
        ```
    """
    try:
        old_path, _ = find_document_path(document_id, from_version)
        new_path, _ = find_document_path(document_id, to_version)

        old_content = old_path.read_text(encoding="utf-8")
        new_content = new_path.read_text(encoding="utf-8")

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{document_id}_v{from_version}.md",
            tofile=f"{document_id}_v{to_version}.md",
        )
        diff_text = "".join(diff_lines)

        if not diff_text:
            return {"diff": "No changes between versions."}

        return {"diff": diff_text}
    except FileNotFoundError as e:
        return {"error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()}
    except OSError as e:
        return {
            "error": ErrorResponse(
                code="READ_ERROR",
                message=format_os_error(e)
            ).model_dump()
        }


@server.tool
def list_documents(
    status: str | None = None,
    document_type: str | None = None,
    author: str | None = None,
) -> list[DocumentSummary]:
    """List all documents with optional filtering.

    Args:
        status: Filter by document status. Common values: Draft, In Review, Approved, Withdrawn.
            Accepts any string value from document frontmatter.
        document_type: Filter by document type. Common values: Design Practice, Guideline, TRS.
            Accepts any string value from document frontmatter.
        author: Filter by author name (case-insensitive substring match).

    Returns:
        List of documents with {id, title, latest_version, status, document_type} for each.
        Returns empty list if no documents match the filters.
        Fields show "NA" if not present in document frontmatter.

    Note:
        Valid values for status and document_type can be configured in folios.toml.

    Example:
        Tool call:
        ```json
        {"tool": "list_documents", "parameters": {"status": "Approved", "document_type": "Design Practice"}}
        ```

        Response:
        ```json
        [
          {"id": 123456, "title": "Stress Analysis", "latest_version": 2, "status": "Approved", "document_type": "Design Practice"},
          {"id": 789012, "title": "Fatigue Analysis", "latest_version": 1, "status": "Approved", "document_type": "Design Practice"}
        ]
        ```
    """
    return scan_documents(status=status, doc_type=document_type, author=author)


@server.tool
def list_document_versions(document_id: int) -> dict:
    """List all available versions of a specific document.

    Args:
        document_id: Unique numeric identifier of the document.

    Returns:
        On success: {"versions": [{version, date, status, author}, ...]}
        On error: {"error": {"code": "NOT_FOUND", "message": "..."}}

    Example:
        Tool call:
        ```json
        {"tool": "list_document_versions", "parameters": {"document_id": 123456}}
        ```

        Response:
        ```json
        {
          "versions": [
            {"version": 1, "date": "2025-01-10", "status": "Approved", "author": "J. Smith"},
            {"version": 2, "date": "2025-02-15", "status": "Approved", "author": "J. Smith"}
          ]
        }
        ```
    """
    versions = []
    for doc_id, doc_version, path in get_all_document_files():
        if doc_id != document_id:
            continue

        try:
            metadata, _ = parse_document(path, doc_id, doc_version)
            versions.append(
                VersionInfo(
                    version=doc_version,
                    date=metadata.get("date", "NA"),
                    status=metadata.get("status", "NA"),
                    author=metadata.get("author", "NA"),
                )
            )
        except (ValueError, KeyError, OSError):
            continue  # Skip malformed or unreadable documents

    if not versions:
        return {
            "error": ErrorResponse(
                code="NOT_FOUND", message=f"Document {document_id} not found"
            ).model_dump()
        }

    sorted_versions = sorted(versions, key=lambda v: v.version)
    return {"versions": [v.model_dump() for v in sorted_versions]}


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run the Folios MCP server."""
    global _cli_folios_path

    parser = argparse.ArgumentParser(description="Folios MCP Server")
    parser.add_argument(
        "--folios-path",
        type=Path,
        help="Path to the folder containing versioned documents",
    )
    args = parser.parse_args()

    # Determine path: CLI flag > env var > error
    if args.folios_path:
        _cli_folios_path = args.folios_path
    elif not os.environ.get("FOLIOS_PATH"):
        print(
            "Error: No documents folder specified.\n\n"
            "Please provide the path to your documents folder using either:\n"
            "  --folios-path /path/to/documents\n"
            "  FOLIOS_PATH=/path/to/documents environment variable",
            file=sys.stderr,
        )
        sys.exit(1)

    server.run(show_banner=False)


if __name__ == "__main__":  # pragma: no cover
    main()
