"""Tests for edge cases and malformed documents."""

import pytest
from pathlib import Path
from unittest.mock import patch

from folios.server import get_all_document_files


class TestMalformedDocuments:
    """Tests for handling malformed documents."""

    def test_unusual_yaml_values_accepted(
        self, set_documents_env: Path, create_document, malformed_frontmatter_content: str, server_tools
    ):
        """Document with unusual YAML values is accepted with flexible parsing."""
        create_document(3001, 1, malformed_frontmatter_content)

        result = server_tools.get_document_metadata.fn(3001, 1)

        # Flexible metadata accepts unusual values
        assert "metadata" in result
        assert result["metadata"]["id"] == 3001

    def test_missing_frontmatter_delimiters_returns_error(
        self, set_documents_env: Path, create_document, missing_delimiter_content: str, server_tools
    ):
        """Document without closing --- returns error."""
        create_document(3002, 1, missing_delimiter_content)

        result = server_tools.get_document_metadata.fn(3002, 1)

        assert "error" in result
        assert result["error"]["code"] == "INVALID_FORMAT"

    def test_no_frontmatter_works_with_defaults(
        self, set_documents_env: Path, create_document, no_frontmatter_content: str, server_tools
    ):
        """Document without frontmatter works with NA defaults."""
        create_document(3003, 1, no_frontmatter_content)

        result = server_tools.get_document_metadata.fn(3003, 1)

        assert "metadata" in result
        assert result["metadata"]["id"] == 3003
        assert result["metadata"]["title"] == "Just Content"
        assert result["metadata"]["author"] == "NA"
        assert result["metadata"]["date"] == "NA"

    def test_empty_file_returns_error(
        self, set_documents_env: Path, create_document, empty_file_content: str, server_tools
    ):
        """Empty document file returns error."""
        create_document(3004, 1, empty_file_content)

        result = server_tools.get_document_metadata.fn(3004, 1)

        assert "error" in result
        assert result["error"]["code"] == "INVALID_FORMAT"

    def test_get_document_returns_raw_content_even_if_malformed(
        self, set_documents_env: Path, create_document, malformed_frontmatter_content: str, server_tools
    ):
        """get_document returns raw content regardless of format validity."""
        create_document(3005, 1, malformed_frontmatter_content)

        result = server_tools.get_document_content.fn(3005, 1)

        # get_document just reads the file, doesn't parse
        assert "content" in result
        assert "error" not in result


class TestListSkipsMalformed:
    """Tests for list operations skipping malformed documents."""

    def test_list_documents_includes_partial_metadata(
        self,
        set_documents_env: Path,
        create_document,
        valid_doc_content: str,
        server_tools,
    ):
        """list_documents includes docs with partial metadata showing NA."""
        create_document(4001, 1, valid_doc_content)
        # Create doc with partial frontmatter (valid structure but missing fields)
        partial_content = """---
document_type: "Guideline"
---

# Partial Doc

Content here.
"""
        create_document(4002, 1, partial_content)

        result = server_tools.list_documents.fn()

        assert len(result) == 2
        # Check the partial doc shows NA for missing fields
        partial_doc = next(d for d in result if d.id == 4002)
        assert partial_doc.status == "NA"
        assert partial_doc.title == "Partial Doc"

    def test_list_documents_skips_unparseable(
        self,
        set_documents_env: Path,
        create_document,
        valid_doc_content: str,
        missing_title_content: str,
        server_tools,
    ):
        """list_documents excludes documents that can't be parsed at all."""
        create_document(4003, 1, valid_doc_content)
        create_document(4004, 1, missing_title_content)

        result = server_tools.list_documents.fn()

        assert len(result) == 1
        assert result[0].id == 4003

    def test_list_versions_skips_unparseable_versions(
        self,
        set_documents_env: Path,
        create_document,
        valid_doc_content: str,
        missing_title_content: str,
        server_tools,
    ):
        """list_versions excludes versions that can't be parsed."""
        create_document(4003, 1, valid_doc_content)
        create_document(4003, 2, missing_title_content)

        result = server_tools.list_document_versions.fn(4003)

        assert "versions" in result
        assert len(result["versions"]) == 1
        assert result["versions"][0]["version"] == 1

    def test_list_versions_includes_flexible_metadata(
        self,
        set_documents_env: Path,
        create_document,
        valid_doc_content: str,
        malformed_frontmatter_content: str,
        server_tools,
    ):
        """list_versions includes versions with unusual but valid frontmatter."""
        create_document(4005, 1, valid_doc_content)
        create_document(4005, 2, malformed_frontmatter_content)

        result = server_tools.list_document_versions.fn(4005)

        assert "versions" in result
        assert len(result["versions"]) == 2

    def test_all_versions_unparseable_returns_error(
        self, set_documents_env: Path, create_document, missing_title_content: str, server_tools
    ):
        """If all versions of a document are unparseable, list_versions returns error."""
        create_document(4004, 1, missing_title_content)
        create_document(4004, 2, missing_title_content)

        result = server_tools.list_document_versions.fn(4004)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestPartialMetadata:
    """Tests for documents with partial/missing metadata fields."""

    def test_partial_frontmatter_shows_na(
        self, set_documents_env: Path, create_document, partial_frontmatter_content: str, server_tools
    ):
        """Missing non-critical fields display 'NA' in list_documents."""
        create_document(5001, 1, partial_frontmatter_content)

        result = server_tools.list_documents.fn()

        assert len(result) == 1
        doc = result[0]
        assert doc.id == 5001
        assert doc.title == "Partial Document"
        assert doc.status == "NA"
        # document_type is "Guideline" in partial_frontmatter_content fixture
        assert doc.document_type == "Guideline"

    def test_partial_metadata_still_filterable(
        self, set_documents_env: Path, create_document, valid_doc_content: str, server_tools
    ):
        """Documents with partial metadata still work with filters on available fields."""
        partial_content = """---
status: "Draft"
---

# Has Title

Content here.
"""
        create_document(5002, 1, partial_content)

        # Filter by available field works
        result = server_tools.list_documents.fn(status="Draft")
        assert len(result) == 1
        assert result[0].id == 5002

        # document_type shows NA since not provided
        assert result[0].document_type == "NA"


class TestFilenameEdgeCases:
    """Tests for filename pattern edge cases."""

    def test_ignores_non_matching_filenames(
        self, set_documents_env: Path, create_document, valid_doc_content: str, server_tools
    ):
        """Files not matching {id}_v{version}.md pattern ignored."""
        # Create valid document
        create_document(6001, 1, valid_doc_content)

        # Create non-matching files
        (set_documents_env / "readme.md").write_text("# Readme")
        (set_documents_env / "notes.txt").write_text("Notes")
        (set_documents_env / "invalid_name.md").write_text("---\nid: 1\n---\n# Test")
        (set_documents_env / "6001.md").write_text("Missing version")
        (set_documents_env / "v1.md").write_text("Missing id")

        result = server_tools.list_documents.fn()

        assert len(result) == 1
        assert result[0].id == 6001

    def test_handles_large_version_numbers(
        self, set_documents_env: Path, create_document, server_tools
    ):
        """Large version numbers handled correctly."""
        content = """---
document_type: "Guideline"
author: "Author"
reviewer: "Reviewer"
approver: "Approver"
date: "2025-01-01"
status: "Draft"
---

# Large Version

Content here.
"""
        create_document(6002, 999, content)

        result = server_tools.list_documents.fn()
        assert len(result) == 1
        assert result[0].latest_version == 999

    def test_handles_large_document_ids(
        self, set_documents_env: Path, create_document, server_tools
    ):
        """Large document IDs handled correctly."""
        content = """---
document_type: "Guideline"
author: "Author"
reviewer: "Reviewer"
approver: "Approver"
date: "2025-01-01"
status: "Draft"
---

# Large ID

Content here.
"""
        create_document(999999, 1, content)

        result = server_tools.list_documents.fn()
        assert len(result) == 1
        assert result[0].id == 999999


class TestDiffEdgeCases:
    """Additional diff edge cases."""

    def test_comparing_same_version_twice(
        self, set_documents_env: Path, create_document, valid_doc_content: str, server_tools
    ):
        """Comparing version with itself returns no changes."""
        create_document(7001, 1, valid_doc_content)

        result = server_tools.diff_document_versions.fn(7001, 1, 1)

        assert "diff" in result
        assert result["diff"] == "No changes between versions."

    def test_reversed_version_order(
        self, set_documents_env: Path, create_document, valid_doc_content: str, valid_doc_v2_content: str, server_tools
    ):
        """old_version > new_version still produces valid diff (reversed)."""
        create_document(7002, 1, valid_doc_content)
        create_document(7002, 2, valid_doc_v2_content)

        # Compare v2 -> v1 (reversed)
        result = server_tools.diff_document_versions.fn(7002, 2, 1)

        assert "diff" in result
        # Diff should show changes, just in reverse direction
        assert "---" in result["diff"]


class TestFileScanningErrors:
    """Tests for error handling during file system scanning."""

    def test_oserror_during_is_file_check_skips_file(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """OSError during is_file() check should skip that file gracefully."""
        create_document(8001, 1, valid_doc_content)
        create_document(8002, 1, valid_doc_content)

        original_is_file = Path.is_file

        def mock_is_file(self):
            if "8001" in str(self):
                raise OSError("Simulated I/O error")
            return original_is_file(self)

        with patch.object(Path, "is_file", mock_is_file):
            result = get_all_document_files(set_documents_env)

        # Only 8002 should be returned, 8001 skipped due to OSError
        doc_ids = [doc_id for doc_id, _, _ in result]
        assert 8002 in doc_ids
        assert 8001 not in doc_ids
