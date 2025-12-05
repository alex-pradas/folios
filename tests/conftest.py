"""Shared pytest fixtures for Folios MCP server tests."""

import pytest
from pathlib import Path


@pytest.fixture
def documents_path(tmp_path: Path) -> Path:
    """Create isolated documents directory."""
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir()
    return docs_dir


@pytest.fixture
def set_documents_env(documents_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set FOLIOS_PATH environment variable."""
    monkeypatch.setenv("FOLIOS_PATH", str(documents_path))
    return documents_path


@pytest.fixture
def create_document(documents_path: Path):
    """Factory fixture to create test documents."""

    def _create(doc_id: int, version: int, content: str) -> Path:
        filename = f"{doc_id}_v{version}.md"
        filepath = documents_path / filename
        filepath.write_text(content, encoding="utf-8")
        return filepath

    return _create


@pytest.fixture
def valid_doc_content() -> str:
    """Return valid document content with complete frontmatter."""
    return """---
type: "Design Practice"
author: "Test Author"
reviewer: "Test Reviewer"
approver: "Test Approver"
date: "2025-01-01"
status: "Draft"
---

# Test Document

Test content paragraph.

## Section One

More content here.

## Section Two

Final section content.
"""


@pytest.fixture
def valid_doc_v2_content() -> str:
    """Return valid document content for version 2."""
    return """---
type: "Design Practice"
author: "Test Author"
reviewer: "Test Reviewer"
approver: "Test Approver"
date: "2025-02-01"
status: "Approved"
---

# Test Document

Updated test content paragraph with changes.

## Section One

Modified content here.

## Section Two

Final section content.

## Section Three

New section added in v2.
"""


@pytest.fixture
def partial_frontmatter_content() -> str:
    """Document with missing optional metadata fields."""
    return """---
type: "Guideline"
---

# Partial Document

Body text without full metadata.
"""


@pytest.fixture
def malformed_frontmatter_content() -> str:
    """Document with invalid YAML in frontmatter."""
    return """---
type: [invalid
author: "Bad YAML
---

# Content
"""


@pytest.fixture
def missing_delimiter_content() -> str:
    """Document missing closing frontmatter delimiter."""
    return """---
type: "Guideline"
author: "Test Author"
"""


@pytest.fixture
def no_frontmatter_content() -> str:
    """Document with no frontmatter at all."""
    return """# Just Content

No frontmatter here.
"""


@pytest.fixture
def empty_file_content() -> str:
    """Empty document file."""
    return ""


@pytest.fixture
def sample_docs(set_documents_env: Path, create_document, valid_doc_content: str, valid_doc_v2_content: str):
    """Create a set of sample documents for testing."""
    # Document 1001 with versions 1 and 2
    create_document(1001, 1, valid_doc_content)
    create_document(1001, 2, valid_doc_v2_content)

    # Document 1002 - different type and status
    doc_1002 = """---
type: "Guideline"
author: "Another Author"
reviewer: "Another Reviewer"
approver: "Another Approver"
date: "2025-01-15"
status: "In Review"
---

# Second Document

Second document content.
"""
    create_document(1002, 1, doc_1002)

    # Document 1003 - single version, different author
    doc_1003 = """---
type: "Best Practice"
author: "Test Author"
reviewer: "Shared Reviewer"
approver: "Shared Approver"
date: "2025-01-20"
status: "Approved"
---

# Third Document

Third document by same author as doc 1001.
"""
    create_document(1003, 1, doc_1003)

    return set_documents_env
