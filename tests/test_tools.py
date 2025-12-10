"""Tests for MCP tool endpoints."""

import pytest
from pathlib import Path


class TestGetDocumentContent:
    """Tests for get_document_content tool."""

    def test_returns_content_for_valid_doc(self, sample_docs: Path, server_tools, valid_doc_content: str):
        """Get document returns content for valid document."""
        result = server_tools.get_document_content.fn(1001, 1)

        assert "content" in result
        assert "error" not in result
        assert "# Test Document" in result["content"]
        assert "---" in result["content"]  # Includes frontmatter

    def test_returns_latest_when_version_none(self, sample_docs: Path, server_tools):
        """Get document returns latest version when version not specified."""
        result = server_tools.get_document_content.fn(1001)

        assert "content" in result
        assert "status: \"Approved\"" in result["content"]  # v2 has Approved status

    def test_nonexistent_document_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent document ID returns graceful error response."""
        result = server_tools.get_document_content.fn(9999)

        assert "error" in result
        assert "content" not in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]

    def test_nonexistent_version_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent version returns graceful error response."""
        result = server_tools.get_document_content.fn(1001, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "version 99" in result["error"]["message"]


class TestGetDocumentMetadata:
    """Tests for get_document_metadata tool."""

    def test_returns_complete_metadata(self, sample_docs: Path, server_tools):
        """Returns all metadata fields for valid document."""
        result = server_tools.get_document_metadata.fn(1001, 1)

        assert "metadata" in result
        assert "error" not in result

        metadata = result["metadata"]
        assert metadata["id"] == 1001
        assert metadata["version"] == 1
        assert metadata["title"] == "Test Document"
        assert metadata["document_type"] == "Design Practice"
        assert metadata["author"] == "Test Author"
        assert metadata["reviewer"] == "Test Reviewer"
        assert metadata["approver"] == "Test Approver"
        assert metadata["status"] == "Draft"

    def test_includes_chapters(self, sample_docs: Path, server_tools):
        """Chapters list populated from H2 headings."""
        result = server_tools.get_document_metadata.fn(1001, 1)

        chapters = result["metadata"]["chapters"]
        assert len(chapters) == 2  # Section One, Section Two (H1 is title)
        assert chapters[0]["title"] == "Section One"
        assert chapters[1]["title"] == "Section Two"

    def test_latest_version_when_not_specified(self, sample_docs: Path, server_tools):
        """Returns metadata for latest version when version=None."""
        result = server_tools.get_document_metadata.fn(1001)

        assert result["metadata"]["version"] == 2
        assert result["metadata"]["status"] == "Approved"

    def test_nonexistent_document_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent document returns graceful error."""
        result = server_tools.get_document_metadata.fn(9999)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_nonexistent_version_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent version returns graceful error."""
        result = server_tools.get_document_metadata.fn(1001, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestGetChapterContent:
    """Tests for get_chapter_content tool."""

    def test_returns_chapter_content(self, sample_docs: Path, server_tools):
        """Get chapter returns content for valid chapter."""
        result = server_tools.get_chapter_content.fn(1001, "Section One", 1)

        assert "content" in result
        assert "error" not in result
        assert "## Section One" in result["content"]
        assert "More content here" in result["content"]
        assert result["chapter_title"] == "Section One"

    def test_returns_latest_version_when_not_specified(self, sample_docs: Path, server_tools):
        """Returns chapter from latest version when version=None."""
        result = server_tools.get_chapter_content.fn(1001, "Section Three")

        assert "content" in result
        # Section Three only exists in v2
        assert "New section added in v2" in result["content"]

    def test_case_insensitive_chapter_match(self, sample_docs: Path, server_tools):
        """Chapter title matching is case-insensitive."""
        result = server_tools.get_chapter_content.fn(1001, "section one", 1)

        assert "content" in result
        assert result["chapter_title"] == "Section One"

    def test_nonexistent_document_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent document returns NOT_FOUND error."""
        result = server_tools.get_chapter_content.fn(9999, "Any Chapter")

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]

    def test_nonexistent_version_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent version returns NOT_FOUND error."""
        result = server_tools.get_chapter_content.fn(1001, "Section One", 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_nonexistent_chapter_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent chapter returns CHAPTER_NOT_FOUND error."""
        result = server_tools.get_chapter_content.fn(1001, "Nonexistent Chapter", 1)

        assert "error" in result
        assert result["error"]["code"] == "CHAPTER_NOT_FOUND"
        assert "Nonexistent Chapter" in result["error"]["message"]

    def test_chapter_in_one_version_not_another(self, sample_docs: Path, server_tools):
        """Chapter existing in v2 but not v1 returns appropriate error."""
        # Section Three only in v2
        result_v1 = server_tools.get_chapter_content.fn(1001, "Section Three", 1)
        result_v2 = server_tools.get_chapter_content.fn(1001, "Section Three", 2)

        assert "error" in result_v1
        assert result_v1["error"]["code"] == "CHAPTER_NOT_FOUND"

        assert "content" in result_v2
        assert "error" not in result_v2


class TestDiffDocumentVersions:
    """Tests for diff_document_versions tool."""

    def test_returns_chapter_grouped_diff(self, sample_docs: Path, server_tools):
        """Returns diff grouped by chapter."""
        result = server_tools.diff_document_versions.fn(1001, 1, 2)

        assert "changes" in result
        assert "error" not in result
        assert isinstance(result["changes"], list)

        # Should have changes in multiple chapters
        chapter_names = [c["chapter"] for c in result["changes"]]
        assert len(chapter_names) > 0

        # Each change should have chapter and diff keys
        for change in result["changes"]:
            assert "chapter" in change
            assert "diff" in change
            assert "---" in change["diff"]
            assert "+++" in change["diff"]

    def test_changes_only_in_metadata(
        self, set_documents_env: Path, create_document, server_tools
    ):
        """Changes only in frontmatter appear under Metadata."""
        v1 = """---
status: "Draft"
---

# Title

## Section One

Content here.
"""
        v2 = """---
status: "Approved"
---

# Title

## Section One

Content here.
"""
        create_document(2001, 1, v1)
        create_document(2001, 2, v2)

        result = server_tools.diff_document_versions.fn(2001, 1, 2)

        assert "changes" in result
        assert len(result["changes"]) == 1
        assert result["changes"][0]["chapter"] == "Metadata"
        assert "Draft" in result["changes"][0]["diff"]
        assert "Approved" in result["changes"][0]["diff"]

    def test_chapter_added(self, sample_docs: Path, server_tools):
        """New chapter in v2 shows as addition."""
        # sample_docs has Section Three only in v2
        result = server_tools.diff_document_versions.fn(1001, 1, 2)

        chapter_names = [c["chapter"] for c in result["changes"]]
        assert "Section Three" in chapter_names

        # Find the Section Three change
        section_three = next(
            c for c in result["changes"] if c["chapter"] == "Section Three"
        )
        # Should show additions (+ lines)
        assert "+" in section_three["diff"]

    def test_chapter_deleted(
        self, set_documents_env: Path, create_document, server_tools
    ):
        """Chapter removed in v2 shows as deletion."""
        v1 = """---
status: "Draft"
---

# Title

## Intro

Intro content.

## To Be Removed

This section will be deleted.

## Conclusion

Final content.
"""
        v2 = """---
status: "Draft"
---

# Title

## Intro

Intro content.

## Conclusion

Final content.
"""
        create_document(2002, 1, v1)
        create_document(2002, 2, v2)

        result = server_tools.diff_document_versions.fn(2002, 1, 2)

        chapter_names = [c["chapter"] for c in result["changes"]]
        assert "To Be Removed" in chapter_names

        # Find the deleted chapter
        deleted = next(c for c in result["changes"] if c["chapter"] == "To Be Removed")
        # Should show deletions (- lines)
        assert "-" in deleted["diff"]

    def test_no_changes_returns_empty_array(
        self, set_documents_env: Path, create_document, valid_doc_content: str, server_tools
    ):
        """Comparing identical content returns empty changes array."""
        create_document(2003, 1, valid_doc_content)
        create_document(2003, 2, valid_doc_content)

        result = server_tools.diff_document_versions.fn(2003, 1, 2)

        assert "changes" in result
        assert result["changes"] == []

    def test_document_without_chapters(
        self, set_documents_env: Path, create_document, server_tools
    ):
        """Document with no H2 headings has all changes under Metadata."""
        v1 = """---
status: "Draft"
---

# Title

Body content version 1.
"""
        v2 = """---
status: "Approved"
---

# Title

Body content version 2.
"""
        create_document(2004, 1, v1)
        create_document(2004, 2, v2)

        result = server_tools.diff_document_versions.fn(2004, 1, 2)

        assert "changes" in result
        assert len(result["changes"]) == 1
        assert result["changes"][0]["chapter"] == "Metadata"

    def test_old_version_not_found_returns_error(self, sample_docs: Path, server_tools):
        """Missing old version returns graceful error."""
        result = server_tools.diff_document_versions.fn(1001, 99, 2)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_new_version_not_found_returns_error(self, sample_docs: Path, server_tools):
        """Missing new version returns graceful error."""
        result = server_tools.diff_document_versions.fn(1001, 1, 99)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_document_not_found_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent document returns graceful error."""
        result = server_tools.diff_document_versions.fn(9999, 1, 2)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestListDocuments:
    """Tests for browse_catalog tool."""

    def test_returns_all_documents(self, sample_docs: Path, server_tools):
        """Returns all documents when no filters."""
        result = server_tools.browse_catalog.fn()

        assert len(result) == 3  # 1001, 1002, 1003
        doc_ids = {doc.id for doc in result}
        assert doc_ids == {1001, 1002, 1003}

    def test_returns_latest_version_info(self, sample_docs: Path, server_tools):
        """Each summary shows latest version number."""
        result = server_tools.browse_catalog.fn()

        doc_1001 = next(d for d in result if d.id == 1001)
        assert doc_1001.latest_version == 2

    def test_filter_by_status(self, sample_docs: Path, server_tools):
        """Status filter returns only matching documents."""
        result = server_tools.browse_catalog.fn(status="Approved")

        assert len(result) == 2  # 1001 (v2) and 1003
        statuses = {doc.status for doc in result}
        assert statuses == {"Approved"}

    def test_filter_by_type(self, sample_docs: Path, server_tools):
        """Type filter returns only matching documents."""
        result = server_tools.browse_catalog.fn(document_type="Guideline")

        assert len(result) == 1
        assert result[0].id == 1002

    def test_filter_by_author(self, sample_docs: Path, server_tools):
        """Author filter with case-insensitive substring match."""
        result = server_tools.browse_catalog.fn(author="Test")

        assert len(result) == 2  # 1001 and 1003 have "Test Author"

    def test_filter_by_author_partial_match(self, sample_docs: Path, server_tools):
        """Partial author name matches."""
        result = server_tools.browse_catalog.fn(author="another")  # lowercase

        assert len(result) == 1
        assert result[0].id == 1002

    def test_combined_filters(self, sample_docs: Path, server_tools):
        """Multiple filters combine with AND logic."""
        result = server_tools.browse_catalog.fn(status="Approved", author="Test")

        assert len(result) == 2  # Both 1001 and 1003 are Approved with Test Author

    def test_no_matches_returns_empty_list(self, sample_docs: Path, server_tools):
        """Filters with no matches return empty list, not error."""
        result = server_tools.browse_catalog.fn(status="Withdrawn")

        assert result == []

    def test_invalid_status_filter_returns_empty(self, sample_docs: Path, server_tools):
        """Invalid status value returns empty list."""
        result = server_tools.browse_catalog.fn(status="NonexistentStatus")

        assert result == []

    def test_empty_documents_directory(self, set_documents_env: Path, server_tools):
        """Empty documents directory returns empty list."""
        result = server_tools.browse_catalog.fn()

        assert result == []


class TestListDocumentVersions:
    """Tests for list_revisions tool."""

    def test_returns_all_versions_sorted(self, sample_docs: Path, server_tools):
        """Returns all versions in ascending order."""
        result = server_tools.list_revisions.fn(1001)

        assert "versions" in result
        assert len(result["versions"]) == 2
        assert result["versions"][0]["version"] == 1
        assert result["versions"][1]["version"] == 2

    def test_version_info_includes_metadata(self, sample_docs: Path, server_tools):
        """Each VersionInfo has version, date, status, author."""
        result = server_tools.list_revisions.fn(1001)

        v1 = result["versions"][0]
        assert v1["version"] == 1
        assert v1["date"] == "2025-01-01"
        assert v1["status"] == "Draft"
        assert v1["author"] == "Test Author"

    def test_single_version_document(self, sample_docs: Path, server_tools):
        """Document with single version returns list of one."""
        result = server_tools.list_revisions.fn(1002)

        assert len(result["versions"]) == 1

    def test_nonexistent_document_returns_error(self, sample_docs: Path, server_tools):
        """Non-existent document returns graceful error."""
        result = server_tools.list_revisions.fn(9999)

        assert "error" in result
        assert "versions" not in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]
