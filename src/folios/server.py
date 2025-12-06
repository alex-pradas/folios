"""Folios MCP Server.

FastMCP server providing versioned document retrieval, metadata access,
and diff capabilities for engineering documents.
"""

import argparse
import difflib
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from importlib.metadata import version

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from pydantic import BaseModel

logger = get_logger("folios")


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


# Pattern for parsing document filenames: {id}_v{version}.md
FILENAME_PATTERN = re.compile(r"^(\d+)_v(\d+)\.md$")

# Pattern for extracting title (first H1 heading)
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Pattern for parsing H2 headings (chapters)
HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)


# =============================================================================
# Parsing Functions
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


def parse_document(
    path: Path, doc_id: int, doc_version: int
) -> tuple[dict[str, Any], str]:
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


# =============================================================================
# Storage Functions
# =============================================================================


def get_all_document_files(docs_path: Path) -> list[tuple[int, int, Path]]:
    """Scan documents directory and return all document files.

    Args:
        docs_path: Path to the documents directory.

    Returns:
        List of tuples (doc_id, version, path) for each document file.
        Returns empty list if directory is inaccessible.
    """
    try:
        if not docs_path.exists():
            return []
    except OSError:
        # Path check failed (network issue, permission, etc.)
        return []

    documents = []
    try:
        for path in docs_path.glob("*.md"):
            try:
                # Verify the path is a file (not a directory with .md extension)
                if not path.is_file():
                    continue
                match = FILENAME_PATTERN.match(path.name)
                if match:
                    doc_id = int(match.group(1))
                    doc_version = int(match.group(2))
                    documents.append((doc_id, doc_version, path))
            except OSError:
                # Skip files that can't be accessed
                continue
    except OSError:
        # Directory listing failed (network issue, permission, etc.)
        return []

    return documents


def get_latest_version(docs_path: Path, doc_id: int) -> int | None:
    """Find the highest version number for a document ID.

    Args:
        docs_path: Path to the documents directory.
        doc_id: The document ID to search for.

    Returns:
        Highest version number, or None if document not found.
    """
    versions = [v for d, v, _ in get_all_document_files(docs_path) if d == doc_id]
    return max(versions) if versions else None


def find_document_path(
    docs_path: Path, doc_id: int, version: int | None = None
) -> tuple[Path, int]:
    """Resolve the file path for a document.

    Args:
        docs_path: Path to the documents directory.
        doc_id: The document ID.
        version: Specific version, or None for latest.

    Returns:
        Tuple of (path to document file, resolved version number).

    Raises:
        FileNotFoundError: If document or version doesn't exist.
    """
    if version is None:
        version = get_latest_version(docs_path, doc_id)
        if version is None:
            raise FileNotFoundError(f"Document {doc_id} not found")

    path = docs_path / f"{doc_id}_v{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Document {doc_id} version {version} not found")

    return path, version


def scan_documents(
    docs_path: Path,
    status: str | None = None,
    doc_type: str | None = None,
    author: str | None = None,
) -> list[DocumentSummary]:
    """Scan and filter documents, returning summaries.

    Args:
        docs_path: Path to the documents directory.
        status: Filter by document status.
        doc_type: Filter by document type.
        author: Filter by author name (case-insensitive substring match).

    Returns:
        List of DocumentSummary for matching documents.
    """
    # Group files by document ID
    doc_versions: dict[int, list[tuple[int, Path]]] = {}
    for doc_id, doc_version, path in get_all_document_files(docs_path):
        if doc_id not in doc_versions:
            doc_versions[doc_id] = []
        doc_versions[doc_id].append((doc_version, path))

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
# Schema Discovery
# =============================================================================

# Maximum unique values for a field to be considered enumerable
MAX_ENUMERABLE_VALUES = 15


def discover_schema(docs_path: Path) -> dict[str, set[str]]:
    """Scan all documents and discover unique values for each frontmatter field.

    Args:
        docs_path: Path to the documents directory.

    Returns:
        Dictionary mapping field names to sets of unique values found.
    """
    field_values: dict[str, set[str]] = {}
    file_count = 0

    for md_file in docs_path.glob("*.md"):
        if not FILENAME_PATTERN.match(md_file.name):
            continue
        try:
            start = time.perf_counter()
            content = md_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                f"Parsed {md_file.name}: {len(frontmatter)} fields in {elapsed_ms:.1f}ms"
            )
            file_count += 1
            for key, value in frontmatter.items():
                if key not in field_values:
                    field_values[key] = set()
                field_values[key].add(str(value))
        except Exception:
            continue

    logger.info(f"Scanned {file_count} documents")
    return field_values


def build_filter_hints(schema: dict[str, set[str]]) -> str:
    """Build description hints for the list_documents tool.

    Args:
        schema: Dictionary mapping field names to sets of unique values.

    Returns:
        Formatted string describing available filters for tool description.
    """
    if not schema:
        return ""

    lines = ["\n\nDiscovered filters:"]
    for field, values in sorted(schema.items()):
        if len(values) <= MAX_ENUMERABLE_VALUES:
            # Enumerable field - list all values
            lines.append(f"  {field}: {', '.join(sorted(values))}")
        else:
            # Free-form field - just show count
            lines.append(f"  {field}: free text ({len(values)} unique values)")

    return "\n".join(lines)


# =============================================================================
# Server Factory
# =============================================================================

__version__ = version("folios")


def create_server(docs_path: Path, filter_hints: str) -> FastMCP:
    """Create and configure the MCP server with tools.

    Args:
        docs_path: Path to the documents directory.
        filter_hints: Dynamic description hints for list_documents.

    Returns:
        Configured FastMCP server instance.
    """
    server = FastMCP(
        name="folios",
        instructions="Retrieve and compare versioned engineering documents. "
        "Documents have metadata (author, status, document_type) and chapters "
        "extracted from headings.",
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
        logger.info(
            f"get_document_content(document_id={document_id}, version={version})"
        )
        start = time.perf_counter()
        try:
            path, _ = find_document_path(docs_path, document_id, version)
            content = path.read_text(encoding="utf-8")
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"Returned {len(content)}B in {elapsed_ms:.1f}ms")
            return {"content": content}
        except FileNotFoundError as e:
            return {
                "error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()
            }
        except UnicodeDecodeError as e:
            return {
                "error": ErrorResponse(
                    code="READ_ERROR", message=f"File encoding error: {e.reason}"
                ).model_dump()
            }
        except MemoryError:
            return {
                "error": ErrorResponse(
                    code="READ_ERROR", message="File too large to read into memory"
                ).model_dump()
            }
        except OSError as e:
            return {
                "error": ErrorResponse(
                    code="READ_ERROR", message=format_os_error(e)
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
        logger.info(
            f"get_document_metadata(document_id={document_id}, version={version})"
        )
        start = time.perf_counter()
        try:
            path, resolved_version = find_document_path(docs_path, document_id, version)
            metadata, _ = parse_document(path, document_id, resolved_version)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"Returned metadata in {elapsed_ms:.1f}ms")
            return {"metadata": metadata}
        except FileNotFoundError as e:
            return {
                "error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()
            }
        except (ValueError, KeyError) as e:
            return {
                "error": ErrorResponse(
                    code="INVALID_FORMAT", message=str(e)
                ).model_dump()
            }
        except OSError as e:
            return {
                "error": ErrorResponse(
                    code="READ_ERROR", message=format_os_error(e)
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
        logger.info(
            f"diff_document_versions(document_id={document_id}, from_version={from_version}, to_version={to_version})"
        )
        start = time.perf_counter()
        try:
            old_path, _ = find_document_path(docs_path, document_id, from_version)
            new_path, _ = find_document_path(docs_path, document_id, to_version)

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
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"Generated diff in {elapsed_ms:.1f}ms")

            if not diff_text:
                return {"diff": "No changes between versions."}

            return {"diff": diff_text}
        except FileNotFoundError as e:
            return {
                "error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()
            }
        except OSError as e:
            return {
                "error": ErrorResponse(
                    code="READ_ERROR", message=format_os_error(e)
                ).model_dump()
            }

    @server.tool(
        description="List all documents with optional filtering." + filter_hints
    )
    def list_documents(
        status: str | None = None,
        document_type: str | None = None,
        author: str | None = None,
    ) -> list[DocumentSummary]:
        """List all documents with optional filtering.

        Args:
            status: Filter by document status.
            document_type: Filter by document type.
            author: Filter by author name (case-insensitive substring match).

        Returns:
            List of documents with {id, title, latest_version, status, document_type} for each.
            Returns empty list if no documents match the filters.
            Fields show "NA" if not present in document frontmatter.

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
        logger.info(
            f"list_documents(status={status}, document_type={document_type}, author={author})"
        )
        start = time.perf_counter()
        results = scan_documents(
            docs_path, status=status, doc_type=document_type, author=author
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"Returned {len(results)} documents in {elapsed_ms:.1f}ms")
        return results

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
        logger.info(f"list_document_versions(document_id={document_id})")
        start = time.perf_counter()
        versions = []
        for doc_id, doc_version, path in get_all_document_files(docs_path):
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

        elapsed_ms = (time.perf_counter() - start) * 1000
        if not versions:
            return {
                "error": ErrorResponse(
                    code="NOT_FOUND", message=f"Document {document_id} not found"
                ).model_dump()
            }

        sorted_versions = sorted(versions, key=lambda v: v.version)
        logger.debug(f"Returned {len(sorted_versions)} versions in {elapsed_ms:.1f}ms")
        return {"versions": [v.model_dump() for v in sorted_versions]}

    return server


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run the Folios MCP server."""
    parser = argparse.ArgumentParser(description="Folios MCP Server")
    parser.add_argument(
        "--folios-path",
        type=Path,
        help="Path to the folder containing versioned documents",
    )
    args = parser.parse_args()

    # Resolve documents path: CLI flag > env var > error
    docs_path = args.folios_path
    if docs_path is None:
        env_path = os.environ.get("FOLIOS_PATH")
        if env_path:
            docs_path = Path(env_path)

    if docs_path is None:
        print(
            "Error: No documents folder specified.\n\n"
            "Please provide the path to your documents folder using either:\n"
            "  --folios-path /path/to/documents\n"
            "  FOLIOS_PATH=/path/to/documents environment variable",
            file=sys.stderr,
        )
        sys.exit(1)

    logger.info(f"Folios v{__version__} starting")
    logger.info(f"Documents path: {docs_path}")

    # Discover schema from existing documents
    start = time.perf_counter()
    schema = discover_schema(docs_path)
    elapsed_ms = (time.perf_counter() - start) * 1000
    filter_hints = build_filter_hints(schema)
    logger.info(f"Schema discovery: {len(schema)} fields in {elapsed_ms:.1f}ms")

    # Create and run server
    server = create_server(docs_path, filter_hints)
    logger.info("Server ready")
    server.run(show_banner=False)


if __name__ == "__main__":  # pragma: no cover
    main()
