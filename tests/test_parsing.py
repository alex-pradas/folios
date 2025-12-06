"""Tests for parsing and storage functions."""

import pytest
from pathlib import Path

from folios.server import (
    parse_frontmatter,
    parse_title,
    parse_chapters,
    parse_document,
    find_document_path,
    get_all_document_files,
    get_latest_version,
    Chapter,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter(self, valid_doc_content: str):
        """Parse complete valid frontmatter."""
        frontmatter, body = parse_frontmatter(valid_doc_content)

        assert frontmatter["type"] == "Design Practice"
        assert frontmatter["author"] == "Test Author"
        assert frontmatter["status"] == "Draft"
        assert "# Test Document" in body

    def test_missing_frontmatter_raises_valueerror(self):
        """Document without --- prefix raises ValueError."""
        content = "# Just a heading\n\nNo frontmatter here."
        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            parse_frontmatter(content)

    def test_invalid_frontmatter_format_raises_valueerror(self, missing_delimiter_content: str):
        """Document with missing closing delimiter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid frontmatter format"):
            parse_frontmatter(missing_delimiter_content)

    def test_quoted_values_unquoted(self):
        """Values in quotes should have quotes removed."""
        content = '''---
type: "Quoted Type"
author: 'Single Quoted'
---

# Title

Body.
'''
        frontmatter, _ = parse_frontmatter(content)
        assert frontmatter["type"] == "Quoted Type"
        assert frontmatter["author"] == "Single Quoted"

    def test_numeric_values_converted(self):
        """Numeric strings converted to integers."""
        content = '''---
type: "Test"
priority: 42
---

# Title

Body.
'''
        frontmatter, _ = parse_frontmatter(content)
        assert frontmatter["priority"] == 42
        assert isinstance(frontmatter["priority"], int)

    def test_empty_frontmatter(self):
        """Empty frontmatter section is valid but produces empty dict."""
        content = '''---
---

Body content.
'''
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter == {}
        assert "Body content" in body

    def test_frontmatter_with_comments_skips_comment_lines(self):
        """Comment lines in frontmatter should be skipped."""
        content = """---
# This is a comment
type: "Guideline"
# Another comment
author: "Test"
---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["type"] == "Guideline"
        assert frontmatter["author"] == "Test"
        assert len(frontmatter) == 2  # Only type and author, no comments

    def test_frontmatter_with_lines_missing_colon_skips_them(self):
        """Lines without colons in frontmatter should be skipped."""
        content = """---
type: "Guideline"
this line has no colon
author: "Test"
another malformed line
---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["type"] == "Guideline"
        assert frontmatter["author"] == "Test"
        assert len(frontmatter) == 2  # Only valid key:value pairs

    def test_frontmatter_with_empty_lines_skips_them(self):
        """Empty lines in frontmatter should be skipped."""
        content = """---

type: "Guideline"

author: "Test"

---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["type"] == "Guideline"
        assert frontmatter["author"] == "Test"


class TestParseTitle:
    """Tests for parse_title function."""

    def test_extracts_h1_title(self):
        """H1 heading (# Title) extracted as title."""
        content = "# Document Title\n\nContent.\n\n## Section"
        title = parse_title(content)
        assert title == "Document Title"

    def test_extracts_first_h1_only(self):
        """Only the first H1 heading is used as title."""
        content = "# First Title\n\nContent.\n\n# Second Title"
        title = parse_title(content)
        assert title == "First Title"

    def test_missing_h1_raises_valueerror(self):
        """Document without H1 heading raises ValueError."""
        content = "## Only H2\n\nContent."
        with pytest.raises(ValueError, match="missing title"):
            parse_title(content)


class TestParseChapters:
    """Tests for parse_chapters function."""

    def test_extracts_h2_headings(self):
        """H2 headings (## Title) extracted as chapters."""
        content = "## Section One\n\nContent.\n\n## Section Two"
        chapters = parse_chapters(content)

        assert len(chapters) == 2
        assert chapters[0] == Chapter(title="Section One")
        assert chapters[1] == Chapter(title="Section Two")

    def test_ignores_h1_headings(self):
        """H1 headings are not included (they are titles)."""
        content = "# Title\n\n## Sub One\n\n## Sub Two"
        chapters = parse_chapters(content)

        assert len(chapters) == 2
        assert chapters[0].title == "Sub One"
        assert chapters[1].title == "Sub Two"

    def test_ignores_h3_and_deeper(self):
        """H3+ headings not included in chapters."""
        content = "## Section\n\n### Deep Heading\n\n#### Deeper"
        chapters = parse_chapters(content)

        assert len(chapters) == 1
        assert chapters[0].title == "Section"

    def test_empty_content_returns_empty_list(self):
        """No headings returns empty list."""
        chapters = parse_chapters("")
        assert chapters == []

        chapters = parse_chapters("Just plain text without headings.")
        assert chapters == []


class TestParseDocument:
    """Tests for parse_document function."""

    def test_valid_document_returns_metadata_and_body(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Complete document returns DocumentMetadata and body."""
        path = create_document(1001, 1, valid_doc_content)
        metadata, body = parse_document(path, 1001, 1)

        assert metadata.id == 1001
        assert metadata.version == 1
        assert metadata.title == "Test Document"
        assert metadata.type == "Design Practice"
        assert metadata.author == "Test Author"
        assert metadata.status == "Draft"
        assert len(metadata.chapters) == 2  # Section One, Section Two (H1 is title)
        assert "Test content paragraph" in body

    def test_nonexistent_file_raises_filenotfound(self, tmp_path: Path):
        """Missing file raises FileNotFoundError."""
        fake_path = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_document(fake_path, 1001, 1)

    def test_invalid_frontmatter_raises_valueerror(
        self, set_documents_env: Path, create_document, no_frontmatter_content: str
    ):
        """Document without frontmatter raises ValueError."""
        path = create_document(9999, 1, no_frontmatter_content)
        with pytest.raises(ValueError):
            parse_document(path, 9999, 1)

    def test_missing_required_field_raises_keyerror(
        self, set_documents_env: Path, create_document, partial_frontmatter_content: str
    ):
        """Missing required frontmatter field raises KeyError."""
        path = create_document(1002, 1, partial_frontmatter_content)
        with pytest.raises(KeyError):
            parse_document(path, 1002, 1)


class TestFindDocumentPath:
    """Tests for find_document_path function."""

    def test_finds_specific_version(self, sample_docs: Path, create_document):
        """Returns path and version for specific version."""
        path, version = find_document_path(1001, 1)
        assert path.exists()
        assert path.name == "1001_v1.md"
        assert version == 1

    def test_finds_latest_version_when_none(self, sample_docs: Path):
        """Returns highest version when version=None."""
        path, version = find_document_path(1001, None)
        assert path.exists()
        assert path.name == "1001_v2.md"  # v2 is latest
        assert version == 2

    def test_nonexistent_doc_raises_filenotfound(self, sample_docs: Path):
        """Missing document raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Document 9999 not found"):
            find_document_path(9999)

    def test_nonexistent_version_raises_filenotfound(self, sample_docs: Path):
        """Missing version raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="version 99 not found"):
            find_document_path(1001, 99)


class TestGetAllDocumentFiles:
    """Tests for get_all_document_files function."""

    def test_returns_all_documents(self, sample_docs: Path):
        """Returns all document files."""
        files = get_all_document_files()

        # sample_docs creates: 1001_v1, 1001_v2, 1002_v1, 1003_v1
        assert len(files) == 4

        doc_ids = {f[0] for f in files}
        assert doc_ids == {1001, 1002, 1003}

    def test_empty_directory_returns_empty_list(self, set_documents_env: Path):
        """Empty documents directory returns empty list."""
        files = get_all_document_files()
        assert files == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path: Path, monkeypatch):
        """Missing documents directory returns empty list."""
        monkeypatch.setenv("FOLIOS_PATH", str(tmp_path / "nonexistent"))
        files = get_all_document_files()
        assert files == []

    def test_ignores_non_matching_filenames(self, set_documents_env: Path):
        """Files not matching {id}_v{version}.md pattern ignored."""
        # Create non-matching files
        (set_documents_env / "readme.md").write_text("# Readme")
        (set_documents_env / "notes.txt").write_text("Notes")
        (set_documents_env / "invalid_name.md").write_text("Invalid")

        files = get_all_document_files()
        assert files == []


class TestGetLatestVersion:
    """Tests for get_latest_version function."""

    def test_returns_highest_version(self, sample_docs: Path):
        """Returns highest version number for document."""
        version = get_latest_version(1001)
        assert version == 2

    def test_single_version_document(self, sample_docs: Path):
        """Returns version for document with single version."""
        version = get_latest_version(1002)
        assert version == 1

    def test_nonexistent_document_returns_none(self, sample_docs: Path):
        """Returns None for non-existent document."""
        version = get_latest_version(9999)
        assert version is None
