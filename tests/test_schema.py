"""Tests for schema discovery from documents."""

import pytest
from pathlib import Path

from folios.server import (
    discover_schema,
    build_filter_hints,
    MAX_ENUMERABLE_VALUES,
)


class TestDiscoverSchema:
    """Tests for discover_schema function."""

    def test_returns_empty_dict_for_empty_directory(self, documents_path: Path):
        """Returns empty dict when no documents exist."""
        result = discover_schema(documents_path)
        assert result == {}

    def test_discovers_fields_from_single_document(
        self, documents_path: Path, create_document, valid_doc_content: str
    ):
        """Discovers fields from a single document."""
        create_document(1001, 1, valid_doc_content)

        result = discover_schema(documents_path)

        assert "status" in result
        assert "Draft" in result["status"]
        assert "document_type" in result
        assert "Design Practice" in result["document_type"]
        assert "author" in result
        assert "Test Author" in result["author"]

    def test_aggregates_values_from_multiple_documents(
        self, documents_path: Path, create_document
    ):
        """Aggregates unique values from multiple documents."""
        doc1 = """---
status: "Draft"
author: "Author A"
---

# Doc 1
"""
        doc2 = """---
status: "Approved"
author: "Author B"
---

# Doc 2
"""
        doc3 = """---
status: "Draft"
author: "Author A"
---

# Doc 3
"""
        create_document(1001, 1, doc1)
        create_document(1002, 1, doc2)
        create_document(1003, 1, doc3)

        result = discover_schema(documents_path)

        assert result["status"] == {"Draft", "Approved"}
        assert result["author"] == {"Author A", "Author B"}

    def test_handles_documents_without_frontmatter(
        self, documents_path: Path, create_document, no_frontmatter_content: str
    ):
        """Documents without frontmatter don't contribute fields."""
        create_document(1001, 1, no_frontmatter_content)

        result = discover_schema(documents_path)

        assert result == {}

    def test_skips_malformed_documents(
        self, documents_path: Path, create_document, missing_delimiter_content: str
    ):
        """Malformed documents are skipped gracefully."""
        create_document(1001, 1, missing_delimiter_content)

        result = discover_schema(documents_path)

        # Should not crash, returns empty or partial result
        assert isinstance(result, dict)

    def test_ignores_non_matching_filenames(
        self, documents_path: Path, create_document, valid_doc_content: str
    ):
        """Files not matching {id}_v{version}.md are ignored."""
        # Create valid document
        create_document(1001, 1, valid_doc_content)

        # Create non-matching files
        (documents_path / "readme.md").write_text("---\nstatus: Ignored\n---\n# Readme")
        (documents_path / "notes.txt").write_text("Notes")

        result = discover_schema(documents_path)

        # Should only have values from the valid document
        assert "Ignored" not in result.get("status", set())
        assert "Draft" in result["status"]

    def test_converts_numeric_values_to_strings(
        self, documents_path: Path, create_document
    ):
        """Numeric frontmatter values are converted to strings."""
        doc = """---
priority: 42
status: "Draft"
---

# Doc
"""
        create_document(1001, 1, doc)

        result = discover_schema(documents_path)

        assert "42" in result["priority"]
        assert isinstance(list(result["priority"])[0], str)


class TestBuildFilterHints:
    """Tests for build_filter_hints function."""

    def test_returns_empty_string_for_empty_schema(self):
        """Returns empty string when schema is empty."""
        result = build_filter_hints({})
        assert result == ""

    def test_lists_enumerable_fields(self):
        """Fields with few values are listed completely."""
        schema = {
            "status": {"Draft", "Approved", "Withdrawn"},
            "document_type": {"Guideline", "Best Practice"},
        }

        result = build_filter_hints(schema)

        assert "Discovered filters:" in result
        assert "status:" in result
        assert "Draft" in result
        assert "Approved" in result
        assert "document_type:" in result
        assert "Guideline" in result

    def test_shows_count_for_high_cardinality_fields(self):
        """Fields with many values show count instead of listing."""
        # Create a field with more than MAX_ENUMERABLE_VALUES unique values
        schema = {
            "author": {f"Author {i}" for i in range(MAX_ENUMERABLE_VALUES + 5)},
            "status": {"Draft", "Approved"},
        }

        result = build_filter_hints(schema)

        # Author should show count, not list
        assert "author: free text" in result
        assert f"({MAX_ENUMERABLE_VALUES + 5} unique values)" in result

        # Status should still list values
        assert "Draft" in result
        assert "Approved" in result

    def test_sorts_field_names_alphabetically(self):
        """Field names are sorted alphabetically."""
        schema = {
            "zebra": {"Z"},
            "alpha": {"A"},
            "middle": {"M"},
        }

        result = build_filter_hints(schema)

        alpha_pos = result.find("alpha")
        middle_pos = result.find("middle")
        zebra_pos = result.find("zebra")

        assert alpha_pos < middle_pos < zebra_pos

    def test_sorts_values_alphabetically(self):
        """Values within a field are sorted alphabetically."""
        schema = {
            "status": {"Withdrawn", "Approved", "Draft"},
        }

        result = build_filter_hints(schema)

        # Values should appear in alphabetical order
        approved_pos = result.find("Approved")
        draft_pos = result.find("Draft")
        withdrawn_pos = result.find("Withdrawn")

        assert approved_pos < draft_pos < withdrawn_pos

    def test_threshold_boundary(self):
        """Test behavior at exactly MAX_ENUMERABLE_VALUES."""
        # Exactly at threshold - should list
        schema_at = {"field": {str(i) for i in range(MAX_ENUMERABLE_VALUES)}}
        result_at = build_filter_hints(schema_at)
        assert "free text" not in result_at

        # One over threshold - should summarize
        schema_over = {"field": {str(i) for i in range(MAX_ENUMERABLE_VALUES + 1)}}
        result_over = build_filter_hints(schema_over)
        assert "free text" in result_over


class TestSchemaIntegration:
    """Integration tests for schema discovery with server creation."""

    def test_schema_included_in_tool_description(
        self, documents_path: Path, create_document, valid_doc_content: str
    ):
        """Schema hints are included in list_documents tool description."""
        from folios.server import create_server

        create_document(1001, 1, valid_doc_content)

        schema = discover_schema(documents_path)
        hints = build_filter_hints(schema)
        server = create_server(documents_path, hints)

        # Get the list_documents tool
        list_docs_tool = server._tool_manager._tools.get("list_documents")
        assert list_docs_tool is not None

        # Check that the description includes our hints
        description = list_docs_tool.description
        assert "Discovered filters:" in description
        assert "Draft" in description
