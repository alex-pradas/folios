"""Alexandria - MCP server for versioned document management.

Provides document retrieval, metadata access, versioning, and diff capabilities
for engineering documents stored as markdown files with YAML frontmatter.
"""

from alexandria.server import (
    Chapter,
    DiffResult,
    DocumentMetadata,
    DocumentSummary,
    DocumentStatus,
    DocumentType,
    VersionInfo,
    server,
)

__version__ = "0.1.0"

__all__ = [
    "Chapter",
    "DiffResult",
    "DocumentMetadata",
    "DocumentSummary",
    "DocumentStatus",
    "DocumentType",
    "VersionInfo",
    "server",
    "__version__",
]
