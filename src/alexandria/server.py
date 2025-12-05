"""Alexandria MCP Server.

FastMCP server providing versioned document retrieval, metadata access,
and diff capabilities for engineering documents.
"""

import difflib
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from fastmcp import FastMCP
from pydantic import BaseModel

# =============================================================================
# Type Definitions
# =============================================================================

DocumentStatus = Literal["Draft", "In Review", "Approved", "Withdrawn"]
DocumentType = Literal[
    "Design Practice",
    "Guideline",
    "Best Practice",
    "TRS",  # Technical Requirement Specification
    "DVP",  # Design Verification Plan
    "DVR",  # Detail Verification Review
]

# =============================================================================
# Pydantic Models
# =============================================================================


class Chapter(BaseModel):
    """Represents a document heading (H1 or H2)."""

    level: int  # 1 or 2
    title: str  # Heading text


class DocumentMetadata(BaseModel):
    """Full document metadata including chapters."""

    id: int
    version: int
    title: str
    type: DocumentType
    author: str
    reviewer: str
    approver: str
    date: str
    status: DocumentStatus
    chapters: list[Chapter]  # Parsed from H1/H2 headings


class DocumentSummary(BaseModel):
    """Summary for list_documents results."""

    id: int
    title: str
    latest_version: int  # Most recent version number
    status: DocumentStatus  # Status of latest version
    type: DocumentType


class VersionInfo(BaseModel):
    """Version information for list_versions results."""

    version: int
    date: str
    status: DocumentStatus
    author: str


class DiffResult(BaseModel):
    """Result of comparing two document versions."""

    unified_diff: str
    summary: str | None = None


# =============================================================================
# Configuration
# =============================================================================


def get_documents_path() -> Path:
    """Get the documents path from environment or default.

    Priority:
    1. ALEXANDRIA_DOCUMENTS_PATH environment variable
    2. Default to ./documents in current working directory
    """
    env_path = os.environ.get("ALEXANDRIA_DOCUMENTS_PATH")
    if env_path:
        return Path(env_path)
    return Path.cwd() / "documents"


# Pattern for parsing document filenames: {id}_v{version}.md
FILENAME_PATTERN = re.compile(r"^(\d+)_v(\d+)\.md$")

# Pattern for parsing H1/H2 headings
HEADING_PATTERN = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)

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
        ValueError: If frontmatter is missing or invalid.
    """
    if not content.startswith("---"):
        raise ValueError("Document missing YAML frontmatter")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid frontmatter format")

    frontmatter_yaml = parts[1].strip()
    body = parts[2].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_yaml)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")

    return frontmatter, body


def parse_chapters(content: str) -> list[Chapter]:
    """Extract H1 and H2 headings from document content.

    Args:
        content: Document body content (without frontmatter).

    Returns:
        List of Chapter objects with level and title.
    """
    chapters = []
    for match in HEADING_PATTERN.finditer(content):
        level = len(match.group(1))  # Number of # characters
        title = match.group(2).strip()
        chapters.append(Chapter(level=level, title=title))
    return chapters


def parse_document(path: Path) -> tuple[DocumentMetadata, str]:
    """Parse a document file into metadata and content.

    Args:
        path: Path to the markdown document file.

    Returns:
        Tuple of (DocumentMetadata, body content).

    Raises:
        FileNotFoundError: If document file doesn't exist.
        ValueError: If document format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    chapters = parse_chapters(body)

    metadata = DocumentMetadata(
        id=frontmatter["id"],
        version=frontmatter["version"],
        title=frontmatter["title"],
        type=frontmatter["type"],
        author=frontmatter["author"],
        reviewer=frontmatter["reviewer"],
        approver=frontmatter["approver"],
        date=frontmatter["date"],
        status=frontmatter["status"],
        chapters=chapters,
    )

    return metadata, body


def get_all_document_files() -> list[tuple[int, int, Path]]:
    """Scan documents directory and return all document files.

    Returns:
        List of tuples (doc_id, version, path) for each document file.
    """
    documents_path = get_documents_path()
    if not documents_path.exists():
        return []

    documents = []
    for path in documents_path.glob("*.md"):
        match = FILENAME_PATTERN.match(path.name)
        if match:
            doc_id = int(match.group(1))
            version = int(match.group(2))
            documents.append((doc_id, version, path))

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


def find_document_path(doc_id: int, version: int | None = None) -> Path:
    """Resolve the file path for a document.

    Args:
        doc_id: The document ID.
        version: Specific version, or None for latest.

    Returns:
        Path to the document file.

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

    return path


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
            metadata, _ = parse_document(latest_path)
        except (ValueError, KeyError):
            continue  # Skip malformed documents

        # Apply filters
        if status and metadata.status != status:
            continue
        if doc_type and metadata.type != doc_type:
            continue
        if author and author.lower() not in metadata.author.lower():
            continue

        summaries.append(
            DocumentSummary(
                id=metadata.id,
                title=metadata.title,
                latest_version=latest_version,
                status=metadata.status,
                type=metadata.type,
            )
        )

    return summaries


def generate_diff(
    old_content: str, new_content: str, include_summary: bool = True
) -> DiffResult:
    """Generate a diff between two document versions.

    Args:
        old_content: Content of the older version.
        new_content: Content of the newer version.
        include_summary: Whether to include a change summary.

    Returns:
        DiffResult with unified diff and optional summary.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new")
    )
    unified_diff = "".join(diff_lines)

    summary = None
    if include_summary:
        additions = sum(
            1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
        )
        summary = f"{additions} lines added, {deletions} lines removed"

    return DiffResult(unified_diff=unified_diff, summary=summary)


# =============================================================================
# FastMCP Server
# =============================================================================

server = FastMCP(
    name="alexandria",
    instructions="Retrieve and compare versioned engineering documents. "
    "Documents have metadata (author, status, type) and chapters extracted from headings. "
    "Set ALEXANDRIA_DOCUMENTS_PATH environment variable to configure the documents folder.",
)


@server.tool
def get_document(id: int, version: int | None = None) -> str:
    """Get document content by ID.

    Args:
        id: The numeric document ID.
        version: Specific version number, or None for latest version.

    Returns:
        Full document content (including frontmatter).
    """
    path = find_document_path(id, version)
    return path.read_text(encoding="utf-8")


@server.tool
def get_document_metadata(id: int, version: int | None = None) -> DocumentMetadata:
    """Get document metadata by ID.

    Args:
        id: The numeric document ID.
        version: Specific version number, or None for latest version.

    Returns:
        DocumentMetadata including title, author, status, type, and chapters.
    """
    path = find_document_path(id, version)
    metadata, _ = parse_document(path)
    return metadata


@server.tool
def compare_versions(
    id: int,
    old_version: int,
    new_version: int,
    format: str = "both",
) -> DiffResult:
    """Compare two versions of a document.

    Args:
        id: The numeric document ID.
        old_version: The older version number.
        new_version: The newer version number.
        format: Output format - "unified", "summary", or "both".

    Returns:
        DiffResult with unified diff and/or summary based on format.
    """
    old_path = find_document_path(id, old_version)
    new_path = find_document_path(id, new_version)

    old_content = old_path.read_text(encoding="utf-8")
    new_content = new_path.read_text(encoding="utf-8")

    include_summary = format in ("summary", "both")
    result = generate_diff(old_content, new_content, include_summary)

    if format == "summary":
        result.unified_diff = ""  # Clear diff when only summary requested

    return result


@server.tool
def list_documents(
    status: str | None = None,
    type: str | None = None,
    author: str | None = None,
) -> list[DocumentSummary]:
    """List documents with optional filters.

    Args:
        status: Filter by status (Draft, In Review, Approved, Withdrawn).
        type: Filter by document type (Design Practice, Guideline, etc.).
        author: Filter by author name (case-insensitive substring match).

    Returns:
        List of DocumentSummary with id, title, latest_version, status, and type.
    """
    return scan_documents(status=status, doc_type=type, author=author)


@server.tool
def list_versions(id: int) -> list[VersionInfo]:
    """List all versions of a document.

    Args:
        id: The numeric document ID.

    Returns:
        List of VersionInfo with version number, date, status, and author.
    """
    versions = []
    for doc_id, version, path in get_all_document_files():
        if doc_id != id:
            continue

        try:
            metadata, _ = parse_document(path)
            versions.append(
                VersionInfo(
                    version=metadata.version,
                    date=metadata.date,
                    status=metadata.status,
                    author=metadata.author,
                )
            )
        except (ValueError, KeyError):
            continue  # Skip malformed documents

    if not versions:
        raise FileNotFoundError(f"Document {id} not found")

    return sorted(versions, key=lambda v: v.version)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Run the Alexandria MCP server."""
    server.run()


if __name__ == "__main__":
    main()
