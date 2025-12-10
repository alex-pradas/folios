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
    extract_chapter_content,
    Chapter,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter(self, valid_doc_content: str):
        """Parse complete valid frontmatter."""
        frontmatter, body = parse_frontmatter(valid_doc_content)

        assert frontmatter["document_type"] == "Design Practice"
        assert frontmatter["author"] == "Test Author"
        assert frontmatter["status"] == "Draft"
        assert "# Test Document" in body

    def test_no_frontmatter_returns_empty_dict(self):
        """Document without frontmatter returns empty dict and full content."""
        content = "# Just a heading\n\nNo frontmatter here."
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter == {}
        assert "# Just a heading" in body
        assert "No frontmatter here" in body

    def test_unclosed_frontmatter_raises_valueerror(self, missing_delimiter_content: str):
        """Document with unclosed frontmatter delimiter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid frontmatter format"):
            parse_frontmatter(missing_delimiter_content)

    def test_quoted_values_unquoted(self):
        """Values in quotes should have quotes removed."""
        content = '''---
document_type: "Quoted Type"
author: 'Single Quoted'
---

# Title

Body.
'''
        frontmatter, _ = parse_frontmatter(content)
        assert frontmatter["document_type"] == "Quoted Type"
        assert frontmatter["author"] == "Single Quoted"

    def test_numeric_values_converted(self):
        """Numeric strings converted to integers."""
        content = '''---
document_type: "Test"
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
document_type: "Guideline"
# Another comment
author: "Test"
---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["document_type"] == "Guideline"
        assert frontmatter["author"] == "Test"
        assert len(frontmatter) == 2  # Only document_type and author, no comments

    def test_frontmatter_with_lines_missing_colon_skips_them(self):
        """Lines without colons in frontmatter should be skipped."""
        content = """---
document_type: "Guideline"
this line has no colon
author: "Test"
another malformed line
---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["document_type"] == "Guideline"
        assert frontmatter["author"] == "Test"
        assert len(frontmatter) == 2  # Only valid key:value pairs

    def test_frontmatter_with_empty_lines_skips_them(self):
        """Empty lines in frontmatter should be skipped."""
        content = """---

document_type: "Guideline"

author: "Test"

---

# Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["document_type"] == "Guideline"
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
        """Complete document returns metadata dict and body."""
        path = create_document(1001, 1, valid_doc_content)
        metadata, body = parse_document(path, 1001, 1)

        assert metadata["id"] == 1001
        assert metadata["version"] == 1
        assert metadata["title"] == "Test Document"
        assert metadata["document_type"] == "Design Practice"
        assert metadata["author"] == "Test Author"
        assert metadata["status"] == "Draft"
        assert len(metadata["chapters"]) == 2  # Section One, Section Two (H1 is title)
        assert "Test content paragraph" in body

    def test_nonexistent_file_raises_filenotfound(self, tmp_path: Path):
        """Missing file raises FileNotFoundError."""
        fake_path = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_document(fake_path, 1001, 1)

    def test_no_frontmatter_uses_defaults(
        self, set_documents_env: Path, create_document, no_frontmatter_content: str
    ):
        """Document without frontmatter works with NA defaults."""
        path = create_document(9999, 1, no_frontmatter_content)
        metadata, body = parse_document(path, 9999, 1)

        assert metadata["id"] == 9999
        assert metadata["title"] == "Just Content"
        assert metadata["author"] == "NA"
        assert metadata["date"] == "NA"

    def test_missing_title_raises_valueerror(
        self, set_documents_env: Path, create_document, missing_title_content: str
    ):
        """Document without H1 title raises ValueError."""
        path = create_document(9998, 1, missing_title_content)
        with pytest.raises(ValueError, match="missing title"):
            parse_document(path, 9998, 1)

    def test_partial_frontmatter_uses_defaults(
        self, set_documents_env: Path, create_document, partial_frontmatter_content: str
    ):
        """Missing frontmatter fields use 'NA' defaults."""
        path = create_document(1002, 1, partial_frontmatter_content)
        metadata, _ = parse_document(path, 1002, 1)

        # Core fields have defaults
        assert metadata["author"] == "NA"
        assert metadata["date"] == "NA"
        # Available fields are included
        assert metadata["document_type"] == "Guideline"


class TestFindDocumentPath:
    """Tests for find_document_path function."""

    def test_finds_specific_version(self, sample_docs: Path, documents_path: Path):
        """Returns path and version for specific version."""
        path, version = find_document_path(documents_path, 1001, 1)
        assert path.exists()
        assert path.name == "1001_v1.md"
        assert version == 1

    def test_finds_latest_version_when_none(self, sample_docs: Path, documents_path: Path):
        """Returns highest version when version=None."""
        path, version = find_document_path(documents_path, 1001, None)
        assert path.exists()
        assert path.name == "1001_v2.md"  # v2 is latest
        assert version == 2

    def test_nonexistent_doc_raises_filenotfound(self, sample_docs: Path, documents_path: Path):
        """Missing document raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Document 9999 not found"):
            find_document_path(documents_path, 9999)

    def test_nonexistent_version_raises_filenotfound(self, sample_docs: Path, documents_path: Path):
        """Missing version raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="version 99 not found"):
            find_document_path(documents_path, 1001, 99)


class TestGetAllDocumentFiles:
    """Tests for get_all_document_files function."""

    def test_returns_all_documents(self, sample_docs: Path, documents_path: Path):
        """Returns all document files."""
        files = get_all_document_files(documents_path)

        # sample_docs creates: 1001_v1, 1001_v2, 1002_v1, 1003_v1
        assert len(files) == 4

        doc_ids = {f[0] for f in files}
        assert doc_ids == {1001, 1002, 1003}

    def test_nonexistent_directory_returns_empty_list(self, tmp_path: Path):
        """Missing documents directory returns empty list."""
        nonexistent = tmp_path / "nonexistent"
        files = get_all_document_files(nonexistent)
        assert files == []

    def test_ignores_non_matching_filenames(self, set_documents_env: Path, documents_path: Path):
        """Files not matching {id}_v{version}.md pattern ignored."""
        # Create non-matching files
        (documents_path / "readme.md").write_text("# Readme")
        (documents_path / "notes.txt").write_text("Notes")
        (documents_path / "invalid_name.md").write_text("Invalid")

        files = get_all_document_files(documents_path)
        assert files == []


class TestExtractChapterContent:
    """Tests for extract_chapter_content function."""

    def test_extracts_chapter_by_exact_title(self):
        """Exact title match extracts correct chapter."""
        content = """# Title

## Section One

First section content.

## Section Two

Second section content.
"""
        result = extract_chapter_content(content, "Section One")

        assert result is not None
        matched_title, chapter_content = result
        assert matched_title == "Section One"
        assert "## Section One" in chapter_content
        assert "First section content" in chapter_content
        assert "Section Two" not in chapter_content

    def test_case_insensitive_match(self):
        """Case-insensitive match works when exact match fails."""
        content = """## Section One

Content here.
"""
        result = extract_chapter_content(content, "section one")

        assert result is not None
        matched_title, _ = result
        assert matched_title == "Section One"  # Returns actual title

    def test_exact_match_preferred_over_case_insensitive(self):
        """Exact match takes precedence over case-insensitive."""
        content = """## Test

First content.

## test

Second content.
"""
        result = extract_chapter_content(content, "test")

        assert result is not None
        matched_title, chapter_content = result
        assert matched_title == "test"
        assert "Second content" in chapter_content

    def test_last_chapter_extends_to_end(self):
        """Last chapter includes content to end of document."""
        content = """## First

First content.

## Last

Last content here.
More last content.
"""
        result = extract_chapter_content(content, "Last")

        assert result is not None
        _, chapter_content = result
        assert "Last content here" in chapter_content
        assert "More last content" in chapter_content

    def test_chapter_not_found_returns_none(self):
        """Non-existent chapter returns None."""
        content = """## Existing

Content here.
"""
        result = extract_chapter_content(content, "Nonexistent")

        assert result is None

    def test_no_chapters_returns_none(self):
        """Document with no H2 headings returns None."""
        content = "# Title\n\nJust body text."
        result = extract_chapter_content(content, "Anything")

        assert result is None

    def test_empty_chapter_content(self):
        """Chapter with no content between headings."""
        content = """## Empty

## Next

Has content.
"""
        result = extract_chapter_content(content, "Empty")

        assert result is not None
        _, chapter_content = result
        assert chapter_content.strip() == "## Empty"
