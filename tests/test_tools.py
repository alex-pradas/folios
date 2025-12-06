"""Tests for MCP tool endpoints."""

import pytest
from pathlib import Path

from folios.server import (
    get_document_content,
    get_document_metadata,
    diff_document_versions,
    list_documents,
    list_document_versions,
)


class TestGetDocumentContent:
    """Tests for get_document_content tool."""

    def test_returns_content_for_valid_doc(self, sample_docs: Path, valid_doc_content: str):
        """Get document returns content for valid document."""
        result = get_document_content.fn(1001, 1)

        assert "content" in result
        assert "error" not in result
        assert "# Test Document" in result["content"]
        assert "---" in result["content"]  # Includes frontmatter

    def test_returns_latest_when_version_none(self, sample_docs: Path):
        """Get document returns latest version when version not specified."""
        result = get_document_content.fn(1001)

        assert "content" in result
        assert "status: \"Approved\"" in result["content"]  # v2 has Approved status

    def test_nonexistent_document_returns_error(self, sample_docs: Path):
        """Non-existent document ID returns graceful error response."""
        result = get_document_content.fn(9999)

        assert "error" in result
        assert "content" not in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]

    def test_nonexistent_version_returns_error(self, sample_docs: Path):
        """Non-existent version returns graceful error response."""
        result = get_document_content.fn(1001, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "version 99" in result["error"]["message"]


class TestGetDocumentMetadata:
    """Tests for get_document_metadata tool."""

    def test_returns_complete_metadata(self, sample_docs: Path):
        """Returns all metadata fields for valid document."""
        result = get_document_metadata.fn(1001, 1)

        assert "metadata" in result
        assert "error" not in result

        metadata = result["metadata"]
        assert metadata["id"] == 1001
        assert metadata["version"] == 1
        assert metadata["title"] == "Test Document"
        assert metadata["type"] == "Design Practice"
        assert metadata["author"] == "Test Author"
        assert metadata["reviewer"] == "Test Reviewer"
        assert metadata["approver"] == "Test Approver"
        assert metadata["status"] == "Draft"

    def test_includes_chapters(self, sample_docs: Path):
        """Chapters list populated from H2 headings."""
        result = get_document_metadata.fn(1001, 1)

        chapters = result["metadata"]["chapters"]
        assert len(chapters) == 2  # Section One, Section Two (H1 is title)
        assert chapters[0]["title"] == "Section One"
        assert chapters[1]["title"] == "Section Two"

    def test_latest_version_when_not_specified(self, sample_docs: Path):
        """Returns metadata for latest version when version=None."""
        result = get_document_metadata.fn(1001)

        assert result["metadata"]["version"] == 2
        assert result["metadata"]["status"] == "Approved"

    def test_nonexistent_document_returns_error(self, sample_docs: Path):
        """Non-existent document returns graceful error."""
        result = get_document_metadata.fn(9999)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_nonexistent_version_returns_error(self, sample_docs: Path):
        """Non-existent version returns graceful error."""
        result = get_document_metadata.fn(1001, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestDiffDocumentVersions:
    """Tests for diff_document_versions tool."""

    def test_returns_unified_diff(self, sample_docs: Path):
        """Returns unified diff between versions."""
        result = diff_document_versions.fn(1001, 1, 2)

        assert "diff" in result
        assert "error" not in result
        assert "---" in result["diff"]
        assert "+++" in result["diff"]

    def test_identical_versions_no_changes(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Comparing identical content returns no changes message."""
        # Create two versions with identical content
        create_document(2001, 1, valid_doc_content)
        create_document(2001, 2, valid_doc_content)

        result = diff_document_versions.fn(2001, 1, 2)

        assert "diff" in result
        assert result["diff"] == "No changes between versions."

    def test_old_version_not_found_returns_error(self, sample_docs: Path):
        """Missing old version returns graceful error."""
        result = diff_document_versions.fn(1001, 99, 2)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_new_version_not_found_returns_error(self, sample_docs: Path):
        """Missing new version returns graceful error."""
        result = diff_document_versions.fn(1001, 1, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_document_not_found_returns_error(self, sample_docs: Path):
        """Non-existent document returns graceful error."""
        result = diff_document_versions.fn(9999, 1, 2)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestListDocuments:
    """Tests for list_documents tool."""

    def test_returns_all_documents(self, sample_docs: Path):
        """Returns all documents when no filters."""
        result = list_documents.fn()

        assert len(result) == 3  # 1001, 1002, 1003
        doc_ids = {doc.id for doc in result}
        assert doc_ids == {1001, 1002, 1003}

    def test_returns_latest_version_info(self, sample_docs: Path):
        """Each summary shows latest version number."""
        result = list_documents.fn()

        doc_1001 = next(d for d in result if d.id == 1001)
        assert doc_1001.latest_version == 2

    def test_filter_by_status(self, sample_docs: Path):
        """Status filter returns only matching documents."""
        result = list_documents.fn(status="Approved")

        assert len(result) == 2  # 1001 (v2) and 1003
        statuses = {doc.status for doc in result}
        assert statuses == {"Approved"}

    def test_filter_by_type(self, sample_docs: Path):
        """Type filter returns only matching documents."""
        result = list_documents.fn(document_type="Guideline")

        assert len(result) == 1
        assert result[0].id == 1002

    def test_filter_by_author(self, sample_docs: Path):
        """Author filter with case-insensitive substring match."""
        result = list_documents.fn(author="Test")

        assert len(result) == 2  # 1001 and 1003 have "Test Author"

    def test_filter_by_author_partial_match(self, sample_docs: Path):
        """Partial author name matches."""
        result = list_documents.fn(author="another")  # lowercase

        assert len(result) == 1
        assert result[0].id == 1002

    def test_combined_filters(self, sample_docs: Path):
        """Multiple filters combine with AND logic."""
        result = list_documents.fn(status="Approved", author="Test")

        assert len(result) == 2  # Both 1001 and 1003 are Approved with Test Author

    def test_no_matches_returns_empty_list(self, sample_docs: Path):
        """Filters with no matches return empty list, not error."""
        result = list_documents.fn(status="Withdrawn")

        assert result == []

    def test_invalid_status_filter_returns_empty(self, sample_docs: Path):
        """Invalid status value returns empty list."""
        result = list_documents.fn(status="NonexistentStatus")

        assert result == []

    def test_empty_documents_directory(self, set_documents_env: Path):
        """Empty documents directory returns empty list."""
        result = list_documents.fn()

        assert result == []


class TestListDocumentVersions:
    """Tests for list_document_versions tool."""

    def test_returns_all_versions_sorted(self, sample_docs: Path):
        """Returns all versions in ascending order."""
        result = list_document_versions.fn(1001)

        assert "versions" in result
        assert len(result["versions"]) == 2
        assert result["versions"][0]["version"] == 1
        assert result["versions"][1]["version"] == 2

    def test_version_info_includes_metadata(self, sample_docs: Path):
        """Each VersionInfo has version, date, status, author."""
        result = list_document_versions.fn(1001)

        v1 = result["versions"][0]
        assert v1["version"] == 1
        assert v1["date"] == "2025-01-01"
        assert v1["status"] == "Draft"
        assert v1["author"] == "Test Author"

    def test_single_version_document(self, sample_docs: Path):
        """Document with single version returns list of one."""
        result = list_document_versions.fn(1002)

        assert len(result["versions"]) == 1

    def test_nonexistent_document_returns_error(self, sample_docs: Path):
        """Non-existent document returns graceful error."""
        result = list_document_versions.fn(9999)

        assert "error" in result
        assert "versions" not in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]
