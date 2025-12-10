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
from fastmcp.resources import FunctionResource
from fastmcp.utilities.logging import get_logger
from pydantic import BaseModel, AnyUrl

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

    code: str  # "NOT_FOUND", "CHAPTER_NOT_FOUND", "INVALID_FORMAT", "MISSING_FIELD", "READ_ERROR"
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


def extract_chapter_content(body: str, chapter_title: str) -> tuple[str, str] | None:
    """Extract content for a specific chapter (H2 section) from document body.

    Args:
        body: Document body content (without frontmatter).
        chapter_title: Title of the chapter to extract.

    Returns:
        Tuple of (matched_title, content) where content includes the H2 heading
        and all text until the next H2 or end of document.
        Returns None if chapter not found.

    Note:
        Matching is exact first, then case-insensitive as fallback.
        If multiple chapters have the same title, returns the first occurrence.
    """
    headings = list(HEADING_PATTERN.finditer(body))

    if not headings:
        return None

    # Find matching chapter (exact match first, then case-insensitive)
    target_idx = None
    matched_title = None

    # Exact match
    for idx, match in enumerate(headings):
        if match.group(1).strip() == chapter_title:
            target_idx = idx
            matched_title = match.group(1).strip()
            break

    # Case-insensitive fallback
    if target_idx is None:
        chapter_title_lower = chapter_title.lower()
        for idx, match in enumerate(headings):
            if match.group(1).strip().lower() == chapter_title_lower:
                target_idx = idx
                matched_title = match.group(1).strip()
                break

    if target_idx is None:
        return None

    # Extract content from heading start to next heading or end
    start_pos = headings[target_idx].start()
    if target_idx + 1 < len(headings):
        end_pos = headings[target_idx + 1].start()
    else:
        end_pos = len(body)

    content = body[start_pos:end_pos].rstrip()
    return (matched_title, content)


def get_chapter_boundaries(content: str) -> list[tuple[str, int, int]]:
    """Get chapter boundaries as (name, start_line, end_line) tuples.

    Args:
        content: Full document content including frontmatter.

    Returns:
        List of (chapter_name, start_line, end_line) tuples.
        Line numbers are 1-indexed.
        First entry is always "Metadata" covering everything before first H2.
        If no H2 headings exist, returns single "Metadata" entry for entire doc.
    """
    lines = content.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return [("Metadata", 1, 1)]

    # Find all H2 heading line numbers (1-indexed)
    h2_positions: list[tuple[str, int]] = []
    for i, line in enumerate(lines, start=1):
        match = HEADING_PATTERN.match(line)
        if match:
            h2_positions.append((match.group(1).strip(), i))

    boundaries: list[tuple[str, int, int]] = []

    if not h2_positions:
        # No chapters - entire document is "Metadata"
        return [("Metadata", 1, total_lines)]

    # Metadata section: line 1 to line before first H2
    first_h2_line = h2_positions[0][1]
    if first_h2_line > 1:
        boundaries.append(("Metadata", 1, first_h2_line - 1))

    # Each chapter: from H2 line to line before next H2 (or end)
    for i, (title, start_line) in enumerate(h2_positions):
        if i + 1 < len(h2_positions):
            end_line = h2_positions[i + 1][1] - 1
        else:
            end_line = total_lines
        boundaries.append((title, start_line, end_line))

    return boundaries


def get_line_to_chapter_map(
    boundaries: list[tuple[str, int, int]]
) -> dict[int, str]:
    """Create a mapping from line number to chapter name.

    Args:
        boundaries: Output from get_chapter_boundaries().

    Returns:
        Dict mapping line number (1-indexed) to chapter name.
    """
    line_map: dict[int, str] = {}
    for chapter_name, start, end in boundaries:
        for line_num in range(start, end + 1):
            line_map[line_num] = chapter_name
    return line_map


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
    def get_chapter_content(
        document_id: int,
        chapter_title: str,
        version: int | None = None,
    ) -> dict:
        """Retrieve the content of a specific chapter (H2 section) from a document.

        Args:
            document_id: Unique numeric identifier of the document.
            chapter_title: Title of the chapter to retrieve (case-insensitive match).
            version: Specific version number. If not provided, uses the latest version.

        Returns:
            On success: {"content": "<chapter content including heading>", "chapter_title": "<matched title>"}
            On error: {"error": {"code": "NOT_FOUND"|"CHAPTER_NOT_FOUND"|"READ_ERROR", "message": "..."}}

        Example:
            Tool call:
            ```json
            {"tool": "get_chapter_content", "parameters": {"document_id": 123456, "chapter_title": "Methodology"}}
            ```

            Response:
            ```json
            {
              "content": "## Methodology\\n\\nThis section describes the methodology...",
              "chapter_title": "Methodology"
            }
            ```
        """
        logger.info(
            f"get_chapter_content(document_id={document_id}, chapter_title={chapter_title!r}, version={version})"
        )
        start = time.perf_counter()
        try:
            path, _ = find_document_path(docs_path, document_id, version)
            content = path.read_text(encoding="utf-8")
            _, body = parse_frontmatter(content)

            result = extract_chapter_content(body, chapter_title)
            if result is None:
                return {
                    "error": ErrorResponse(
                        code="CHAPTER_NOT_FOUND",
                        message=f"Chapter '{chapter_title}' not found in document {document_id}",
                    ).model_dump()
                }

            matched_title, chapter_content = result
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                f"Returned {len(chapter_content)}B chapter content in {elapsed_ms:.1f}ms"
            )
            return {"content": chapter_content, "chapter_title": matched_title}

        except FileNotFoundError as e:
            return {
                "error": ErrorResponse(code="NOT_FOUND", message=str(e)).model_dump()
            }
        except ValueError as e:
            return {
                "error": ErrorResponse(
                    code="INVALID_FORMAT", message=str(e)
                ).model_dump()
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
    def diff_document_versions(
        document_id: int,
        from_version: int,
        to_version: int,
    ) -> dict:
        """Generate a diff between two versions, grouped by chapter.

        Args:
            document_id: Unique numeric identifier of the document.
            from_version: The older version number to compare from.
            to_version: The newer version number to compare to.

        Returns:
            On success: {"changes": [{"chapter": "<name>", "diff": "<unified diff>"}, ...]}
                Only chapters with changes are included.
                "Metadata" covers frontmatter, title, and content before first H2.
            On no changes: {"changes": []}
            On error: {"error": {"code": "NOT_FOUND"|"READ_ERROR", "message": "..."}}

        Example:
            Tool call:
            ```json
            {"tool": "diff_document_versions", "parameters": {"document_id": 123456, "from_version": 1, "to_version": 2}}
            ```

            Response:
            ```json
            {
              "changes": [
                {"chapter": "Metadata", "diff": "--- ...\\n+++ ...\\n@@ -1,5 +1,5 @@\\n..."},
                {"chapter": "Methodology", "diff": "--- ...\\n+++ ...\\n@@ -20,3 +20,5 @@\\n..."}
              ]
            }
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

            # Get chapter boundaries for both versions
            old_boundaries = get_chapter_boundaries(old_content)
            new_boundaries = get_chapter_boundaries(new_content)

            # Build line-to-chapter maps
            old_line_map = get_line_to_chapter_map(old_boundaries)
            new_line_map = get_line_to_chapter_map(new_boundaries)

            # Collect all unique chapter names (preserving order from both versions)
            seen_chapters: set[str] = set()
            all_chapters: list[str] = []
            for name, _, _ in old_boundaries + new_boundaries:
                if name not in seen_chapters:
                    seen_chapters.add(name)
                    all_chapters.append(name)

            # Split content into lines (without line endings for comparison)
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()

            # For each chapter, extract relevant lines and compute diff
            changes: list[dict[str, str]] = []

            for chapter_name in all_chapters:
                # Get line ranges for this chapter in both versions
                old_chapter_lines: list[str] = []
                new_chapter_lines: list[str] = []

                for line_num, line in enumerate(old_lines, start=1):
                    if old_line_map.get(line_num) == chapter_name:
                        old_chapter_lines.append(line)

                for line_num, line in enumerate(new_lines, start=1):
                    if new_line_map.get(line_num) == chapter_name:
                        new_chapter_lines.append(line)

                # Generate diff for this chapter
                diff_lines = list(
                    difflib.unified_diff(
                        old_chapter_lines,
                        new_chapter_lines,
                        fromfile=f"{document_id}_v{from_version}.md",
                        tofile=f"{document_id}_v{to_version}.md",
                        lineterm="",
                    )
                )

                # Only include if there are actual changes
                if diff_lines:
                    diff_text = "\n".join(diff_lines)
                    changes.append({"chapter": chapter_name, "diff": diff_text})

            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                f"Generated chapter-grouped diff ({len(changes)} chapters changed) in {elapsed_ms:.1f}ms"
            )

            return {"changes": changes}

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

    # =========================================================================
    # Resources
    # =========================================================================

    def register_document_resources():
        """Register each document version as a browsable resource."""
        count = 0
        for doc_id, doc_version, path in get_all_document_files(docs_path):
            try:
                metadata, _ = parse_document(path, doc_id, doc_version)
                title = metadata.get("title", "Untitled")
                author = metadata.get("author", "NA")
                status = metadata.get("status", "NA")
                doc_type = metadata.get("document_type", "NA")

                # Capture path in closure for lazy reading
                def make_reader(p: Path):
                    def read() -> str:
                        return p.read_text(encoding="utf-8")

                    return read

                server.add_resource(
                    FunctionResource(
                        uri=AnyUrl(f"folios://documents/{doc_id}/v{doc_version}"),
                        name=f"{title} (v{doc_version})",
                        description=f"Author: {author} | Status: {status} | Type: {doc_type}",
                        mime_type="text/markdown",
                        fn=make_reader(path),
                    )
                )
                count += 1
            except (ValueError, OSError):
                continue  # Skip malformed documents

        logger.info(f"Registered {count} document resources")

    register_document_resources()

    return server


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run the Folios MCP server."""
    parser = argparse.ArgumentParser(description="Folios MCP Server")
    parser.add_argument(
        "--path",
        type=Path,
        help="Path to the folder containing versioned documents",
    )
    args = parser.parse_args()

    # Resolve documents path: CLI flag > env var > error
    docs_path = args.path
    if docs_path is None:
        env_path = os.environ.get("FOLIOS_PATH")
        if env_path:
            docs_path = Path(env_path)

    if docs_path is None:
        print(
            "Error: No documents folder specified.\n\n"
            "Please provide the path to your documents folder using either:\n"
            "  --path /path/to/documents\n"
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
