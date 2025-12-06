"""Tests for MCP resource functionality."""

import pytest
from pathlib import Path

from folios.server import create_server, discover_schema, build_filter_hints


@pytest.fixture
def server_with_docs(documents_path: Path, create_document, valid_doc_content: str):
    """Create server with a single test document."""
    create_document(100001, 1, valid_doc_content)
    schema = discover_schema(documents_path)
    hints = build_filter_hints(schema)
    return create_server(documents_path, hints)


@pytest.fixture
def server_with_multiple_docs(
    documents_path: Path, create_document, valid_doc_content: str, valid_doc_v2_content: str
):
    """Create server with multiple document versions."""
    create_document(100001, 1, valid_doc_content)
    create_document(100001, 2, valid_doc_v2_content)
    create_document(100002, 1, valid_doc_content)
    schema = discover_schema(documents_path)
    hints = build_filter_hints(schema)
    return create_server(documents_path, hints)


class TestResourceListing:
    """Tests for listing document resources."""

    @pytest.mark.anyio
    async def test_resources_list_single_document(self, server_with_docs):
        """Test that a single document is listed as a resource."""
        resources = await server_with_docs.get_resources()

        assert len(resources) == 1
        resource = list(resources.values())[0]
        assert "100001" in str(resource.uri)
        assert "v1" in str(resource.uri)

    @pytest.mark.anyio
    async def test_resources_list_multiple_versions(self, server_with_multiple_docs):
        """Test that multiple document versions are listed as resources."""
        resources = await server_with_multiple_docs.get_resources()

        assert len(resources) == 3  # 100001 v1, v2 and 100002 v1
        uris = [str(r.uri) for r in resources.values()]
        assert any("100001" in uri and "v1" in uri for uri in uris)
        assert any("100001" in uri and "v2" in uri for uri in uris)
        assert any("100002" in uri and "v1" in uri for uri in uris)

    @pytest.mark.anyio
    async def test_resource_metadata_in_name(self, server_with_docs):
        """Test that resource name includes document title and version."""
        resources = await server_with_docs.get_resources()

        resource = list(resources.values())[0]
        assert "Test Document" in resource.name
        assert "v1" in resource.name

    @pytest.mark.anyio
    async def test_resource_metadata_in_description(self, server_with_docs):
        """Test that resource description includes author, status, and type."""
        resources = await server_with_docs.get_resources()

        resource = list(resources.values())[0]
        assert "Test Author" in resource.description
        assert "Draft" in resource.description
        assert "Design Practice" in resource.description

    @pytest.mark.anyio
    async def test_resource_mime_type(self, server_with_docs):
        """Test that resources have text/markdown MIME type."""
        resources = await server_with_docs.get_resources()

        resource = list(resources.values())[0]
        assert resource.mime_type == "text/markdown"

    @pytest.mark.anyio
    async def test_empty_documents_directory(self, documents_path: Path):
        """Test that empty directory returns no resources."""
        schema = discover_schema(documents_path)
        hints = build_filter_hints(schema)
        server = create_server(documents_path, hints)

        resources = await server.get_resources()
        assert resources == {}


class TestResourceReading:
    """Tests for reading document content via resources."""

    @pytest.mark.anyio
    async def test_resource_read_content(self, server_with_docs, valid_doc_content: str):
        """Test reading document content via resource."""
        resources = await server_with_docs.get_resources()
        resource = list(resources.values())[0]

        content = await resource.read()

        # Content should include frontmatter and body
        assert "# Test Document" in content
        assert "Test content paragraph" in content
        assert "document_type:" in content

    @pytest.mark.anyio
    async def test_resource_read_returns_full_document(self, server_with_docs):
        """Test that resource read returns complete document including frontmatter."""
        resources = await server_with_docs.get_resources()
        resource = list(resources.values())[0]

        content = await resource.read()

        # Should have frontmatter delimiters
        assert content.startswith("---")
        assert "---" in content[3:]  # Second delimiter


class TestResourceURIScheme:
    """Tests for the folios:// URI scheme."""

    @pytest.mark.anyio
    async def test_uri_format(self, server_with_docs):
        """Test that URIs follow folios://documents/{id}/v{version} format."""
        resources = await server_with_docs.get_resources()

        uri = str(list(resources.values())[0].uri)
        assert uri.startswith("folios://documents/")
        assert "/v" in uri

    @pytest.mark.anyio
    async def test_uri_contains_document_id(self, server_with_docs):
        """Test that URI contains the document ID."""
        resources = await server_with_docs.get_resources()

        uri = str(list(resources.values())[0].uri)
        assert "100001" in uri

    @pytest.mark.anyio
    async def test_uri_contains_version(self, server_with_docs):
        """Test that URI contains the version number."""
        resources = await server_with_docs.get_resources()

        uri = str(list(resources.values())[0].uri)
        assert "v1" in uri
