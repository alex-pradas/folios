"""Tests for image MCP resource functionality."""

import pytest
from pathlib import Path

from folios.server import create_server, discover_schema, build_filter_hints


@pytest.fixture
def create_image(documents_path: Path):
    """Factory fixture to create test images in {id}_images/ folders."""

    def _create(doc_id: int, filename: str, content: bytes = b"\x89PNG\r\n\x1a\n") -> Path:
        img_dir = documents_path / f"{doc_id}_images"
        img_dir.mkdir(exist_ok=True)
        filepath = img_dir / filename
        filepath.write_bytes(content)
        return filepath

    return _create


@pytest.fixture
def server_with_images(
    documents_path: Path, create_document, create_image, valid_doc_content: str
):
    """Create server with a document and associated images."""
    create_document(100001, 1, valid_doc_content)
    create_image(100001, "diagram.png")
    create_image(100001, "photo.jpg", b"\xff\xd8\xff\xe0")
    schema = discover_schema(documents_path)
    hints = build_filter_hints(schema)
    return create_server(documents_path, hints)


class TestImageResourceRegistration:
    """Tests for image resource discovery and registration."""

    @pytest.mark.anyio
    async def test_image_resources_registered(self, server_with_images):
        """Test that images in {id}_images/ folders are registered as resources."""
        resources = await server_with_images.get_resources()
        uris = [str(r.uri) for r in resources.values()]
        image_uris = [u for u in uris if "images" in u]
        assert len(image_uris) == 2

    @pytest.mark.anyio
    async def test_image_uri_format(self, server_with_images):
        """Test that image URIs follow folios://images/{id}/{filename} format."""
        resources = await server_with_images.get_resources()
        uris = [str(r.uri) for r in resources.values()]
        assert any("folios://images/100001/diagram.png" in u for u in uris)
        assert any("folios://images/100001/photo.jpg" in u for u in uris)

    @pytest.mark.anyio
    async def test_image_resource_name(self, server_with_images):
        """Test that image resource name includes filename and doc ID."""
        resources = await server_with_images.get_resources()
        names = [r.name for r in resources.values()]
        assert "diagram.png (doc 100001)" in names

    @pytest.mark.anyio
    async def test_image_mime_type_png(self, server_with_images):
        """Test that PNG images get correct MIME type."""
        resources = await server_with_images.get_resources()
        for r in resources.values():
            if "diagram.png" in str(r.uri):
                assert r.mime_type == "image/png"
                return
        pytest.fail("PNG resource not found")

    @pytest.mark.anyio
    async def test_image_mime_type_jpg(self, server_with_images):
        """Test that JPG images get correct MIME type."""
        resources = await server_with_images.get_resources()
        for r in resources.values():
            if "photo.jpg" in str(r.uri):
                assert r.mime_type == "image/jpeg"
                return
        pytest.fail("JPG resource not found")

    @pytest.mark.anyio
    async def test_no_images_no_extra_resources(
        self, documents_path: Path, create_document, valid_doc_content: str
    ):
        """Test that server without image folders has no image resources."""
        create_document(100001, 1, valid_doc_content)
        schema = discover_schema(documents_path)
        hints = build_filter_hints(schema)
        server = create_server(documents_path, hints)

        resources = await server.get_resources()
        image_uris = [str(r.uri) for r in resources.values() if "images" in str(r.uri)]
        assert len(image_uris) == 0

    @pytest.mark.anyio
    async def test_unsupported_extension_ignored(
        self, documents_path: Path, create_document, create_image, valid_doc_content: str
    ):
        """Test that non-image files in image folders are ignored."""
        create_document(100001, 1, valid_doc_content)
        create_image(100001, "diagram.png")
        create_image(100001, "notes.txt")
        create_image(100001, "data.csv")

        schema = discover_schema(documents_path)
        hints = build_filter_hints(schema)
        server = create_server(documents_path, hints)

        resources = await server.get_resources()
        image_uris = [str(r.uri) for r in resources.values() if "images" in str(r.uri)]
        assert len(image_uris) == 1  # Only the PNG

    @pytest.mark.anyio
    async def test_non_matching_folder_ignored(
        self, documents_path: Path, create_document, valid_doc_content: str
    ):
        """Test that folders not matching {id}_images pattern are ignored."""
        create_document(100001, 1, valid_doc_content)
        # Create a folder that doesn't match the pattern
        other_dir = documents_path / "misc_images"
        other_dir.mkdir()
        (other_dir / "pic.png").write_bytes(b"\x89PNG")

        schema = discover_schema(documents_path)
        hints = build_filter_hints(schema)
        server = create_server(documents_path, hints)

        resources = await server.get_resources()
        image_uris = [str(r.uri) for r in resources.values() if "images" in str(r.uri)]
        assert len(image_uris) == 0


class TestImageResourceReading:
    """Tests for reading image content via resources."""

    @pytest.mark.anyio
    async def test_read_image_returns_bytes(self, server_with_images):
        """Test that reading an image resource returns bytes."""
        resources = await server_with_images.get_resources()
        for r in resources.values():
            if "diagram.png" in str(r.uri):
                content = await r.read()
                assert isinstance(content, bytes)
                assert content == b"\x89PNG\r\n\x1a\n"
                return
        pytest.fail("PNG resource not found")
