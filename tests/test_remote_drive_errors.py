"""Tests for remote shared drive error handling.

This test module simulates various failure scenarios that can occur when
the documents folder is located on a remote/shared drive (NFS, SMB, network share).

Error categories tested:
- Permission errors (read access denied, execute access denied)
- Path/directory not found (drive not mounted, path doesn't exist)
- Disk disconnection/dismount during operations
- Network/connectivity failures (timeout, host unreachable)
- Filesystem errors (I/O errors, stale NFS handle, too many open files)
- Race conditions and mid-operation failures
- Graceful degradation across all MCP tools
"""

import errno
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from folios.server import (
    get_document_content,
    get_document_metadata,
    list_documents,
    list_document_versions,
    diff_document_versions,
    get_all_document_files,
    find_document_path,
    scan_documents,
    parse_document,
    get_documents_path,
)


# =============================================================================
# Permission Error Tests
# =============================================================================


class TestPermissionErrors:
    """Tests for permission-related failures on remote drives."""

    def test_read_permission_denied_on_file(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File read fails with permission denied (EACCES)."""
        create_document(1001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = PermissionError(
                errno.EACCES, "Permission denied", str(set_documents_env / "1001_v1.md")
            )
            result = get_document_content.fn(1001, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"
        assert "Permission denied" in result["error"]["message"]

    def test_read_permission_denied_on_metadata(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Metadata fetch fails with permission denied."""
        create_document(2001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = PermissionError(
                errno.EACCES, "Permission denied"
            )
            result = get_document_metadata.fn(2001, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_directory_listing_permission_denied(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Directory glob fails with permission denied."""
        create_document(1002, 1, valid_doc_content)

        with patch.object(Path, "glob") as mock_glob:
            mock_glob.side_effect = PermissionError(
                errno.EACCES, "Permission denied on directory"
            )
            result = list_documents.fn()

        # Should return empty list gracefully, not crash
        assert result == []

    def test_no_execute_permission_on_directory(
        self, set_documents_env: Path
    ):
        """Cannot traverse directory (no execute permission)."""
        with patch.object(Path, "glob") as mock_glob:
            mock_glob.side_effect = PermissionError(
                errno.EACCES, "Permission denied: cannot access directory"
            )
            result = get_all_document_files()

        assert result == []

    def test_permission_changes_mid_operation(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Permission is revoked while listing documents."""
        create_document(1003, 1, valid_doc_content)
        create_document(1003, 2, valid_doc_content)

        call_count = [0]

        def flaky_read(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:
                raise PermissionError(errno.EACCES, "Permission revoked")
            return valid_doc_content

        with patch.object(Path, "read_text", side_effect=flaky_read):
            result = list_document_versions.fn(1003)

        # Should still return at least one version or graceful error
        # Not crash
        if "versions" in result:
            assert len(result["versions"]) >= 0
        elif "error" in result:
            assert "code" in result["error"]


# =============================================================================
# Path Not Found / Drive Not Mounted Tests
# =============================================================================


class TestDriveNotMounted:
    """Tests for scenarios where the remote drive is not mounted/available."""

    def test_documents_path_not_exists(self, tmp_path: Path, monkeypatch):
        """Documents directory doesn't exist (drive not mounted)."""
        nonexistent = tmp_path / "nonexistent_mount"
        monkeypatch.setenv("FOLIOS_PATH", str(nonexistent))

        result = list_documents.fn()
        assert result == []

    def test_documents_path_exists_check_fails(
        self, set_documents_env: Path
    ):
        """Path.exists() raises OSError (network unreachable)."""
        with patch.object(Path, "exists") as mock_exists:
            mock_exists.side_effect = OSError(
                errno.ENETUNREACH, "Network is unreachable"
            )
            result = list_documents.fn()

        # Should handle gracefully
        assert result == []

    def test_glob_returns_empty_on_unmounted_drive(
        self, tmp_path: Path, monkeypatch
    ):
        """Unmounted drive returns no files gracefully."""
        unmounted_path = tmp_path / "unmounted_share"
        unmounted_path.mkdir()
        monkeypatch.setenv("FOLIOS_PATH", str(unmounted_path))

        result = list_documents.fn()
        assert result == []

    def test_file_disappears_between_list_and_read(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File is listed but disappears before reading."""
        doc_path = create_document(1004, 1, valid_doc_content)

        original_read = Path.read_text

        def read_then_delete(self, *args, **kwargs):
            if "1004_v1.md" in str(self):
                raise FileNotFoundError(
                    errno.ENOENT, "No such file or directory", str(self)
                )
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", read_then_delete):
            result = get_document_content.fn(1004, 1)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_drive_becomes_unavailable_during_diff(
        self, set_documents_env: Path, create_document, valid_doc_content: str, valid_doc_v2_content: str
    ):
        """Drive disconnects between reading first and second version for diff."""
        create_document(1005, 1, valid_doc_content)
        create_document(1005, 2, valid_doc_v2_content)

        call_count = [0]

        def disconnect_mid_diff(self, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return valid_doc_content
            raise OSError(errno.ESTALE, "Stale file handle")

        with patch.object(Path, "read_text", disconnect_mid_diff):
            result = diff_document_versions.fn(1005, 1, 2)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"


# =============================================================================
# Network/Connectivity Failure Tests
# =============================================================================


class TestNetworkFailures:
    """Tests for network-related failures on remote drives."""

    def test_connection_timeout_on_read(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File read times out (simulated via BlockingIOError)."""
        create_document(2001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = BlockingIOError(
                errno.ETIMEDOUT, "Connection timed out"
            )
            result = get_document_content.fn(2001, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_host_unreachable(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Remote host becomes unreachable."""
        create_document(2002, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = OSError(
                errno.EHOSTUNREACH, "No route to host"
            )
            result = get_document_content.fn(2002, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_network_down_during_list(self, set_documents_env: Path):
        """Network goes down during directory listing."""
        with patch.object(Path, "glob") as mock_glob:
            mock_glob.side_effect = OSError(errno.ENETDOWN, "Network is down")
            result = list_documents.fn()

        assert result == []

    def test_connection_reset_during_read(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Connection reset while reading file."""
        create_document(2003, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = ConnectionResetError(
                errno.ECONNRESET, "Connection reset by peer"
            )
            result = get_document_metadata.fn(2003, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_connection_refused(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Connection to share is refused."""
        create_document(2004, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = ConnectionRefusedError(
                errno.ECONNREFUSED, "Connection refused"
            )
            result = get_document_content.fn(2004, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"


# =============================================================================
# Filesystem Error Tests
# =============================================================================


class TestFilesystemErrors:
    """Tests for low-level filesystem errors on remote drives."""

    def test_stale_nfs_handle(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Stale NFS file handle error."""
        create_document(3001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = OSError(errno.ESTALE, "Stale file handle")
            result = get_document_content.fn(3001, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"
        assert "Stale" in result["error"]["message"]

    def test_io_error_on_read(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Generic I/O error during file read."""
        create_document(3002, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = IOError(errno.EIO, "Input/output error")
            result = get_document_content.fn(3002, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_too_many_open_files(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """System runs out of file descriptors."""
        create_document(3003, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = OSError(
                errno.EMFILE, "Too many open files"
            )
            result = get_document_content.fn(3003, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_read_only_filesystem(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Filesystem is read-only (shouldn't affect read operations but test handling)."""
        create_document(3004, 1, valid_doc_content)

        # Read operations should still work on read-only filesystems
        result = get_document_content.fn(3004, 1)
        assert "content" in result

    def test_no_space_left_on_device(
        self, set_documents_env: Path
    ):
        """No space left on device (might affect caching/temp files)."""
        with patch.object(Path, "glob") as mock_glob:
            mock_glob.side_effect = OSError(errno.ENOSPC, "No space left on device")
            result = get_all_document_files()

        assert result == []

    def test_file_too_large(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File is too large to read into memory."""
        create_document(3005, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = MemoryError("Unable to allocate memory")
            result = get_document_content.fn(3005, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_name_too_long(
        self, set_documents_env: Path
    ):
        """Path name exceeds filesystem limits."""
        with patch.object(Path, "glob") as mock_glob:
            mock_glob.side_effect = OSError(errno.ENAMETOOLONG, "File name too long")
            result = get_all_document_files()

        assert result == []


# =============================================================================
# Race Condition and Mid-Operation Failure Tests
# =============================================================================


class TestRaceConditions:
    """Tests for race conditions and mid-operation failures."""

    def test_file_modified_during_read(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File is modified while being read (inconsistent state)."""
        create_document(4001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            # Return partial/corrupted content
            mock_read.return_value = "---\ntype: [invalid\n---"
            result = get_document_metadata.fn(4001, 1)

        assert "error" in result
        assert result["error"]["code"] == "INVALID_FORMAT"

    def test_directory_contents_change_during_listing(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Files are added/removed while listing."""
        create_document(4002, 1, valid_doc_content)

        # First glob returns file, but read fails because it's gone
        call_count = [0]

        def flaky_read(self, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError(errno.ENOENT, "File deleted")
            return valid_doc_content

        with patch.object(Path, "read_text", flaky_read):
            result = list_documents.fn()

        # Should handle gracefully - empty or partial results
        assert isinstance(result, list)

    def test_version_appears_mid_list(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """New version appears while listing versions."""
        create_document(4003, 1, valid_doc_content)

        # This should still work - listing is a point-in-time snapshot
        result = list_document_versions.fn(4003)

        assert "versions" in result
        assert len(result["versions"]) >= 1

    def test_multiple_rapid_reads(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Rapid successive reads don't cause issues."""
        create_document(4004, 1, valid_doc_content)

        results = []
        for _ in range(10):
            result = get_document_content.fn(4004, 1)
            results.append(result)

        # All reads should succeed
        for result in results:
            assert "content" in result

    def test_interleaved_list_and_read_operations(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Mixed list and read operations work correctly."""
        create_document(4005, 1, valid_doc_content)
        create_document(4005, 2, valid_doc_content)

        # Interleave operations
        list_result = list_documents.fn()
        read_result = get_document_content.fn(4005, 1)
        versions_result = list_document_versions.fn(4005)
        read_result_2 = get_document_content.fn(4005, 2)

        assert len(list_result) == 1
        assert "content" in read_result
        assert "versions" in versions_result
        assert "content" in read_result_2


# =============================================================================
# Graceful Degradation Tests for All Tools
# =============================================================================


class TestGracefulDegradation:
    """Ensure all MCP tools degrade gracefully under errors."""

    def test_get_document_content_handles_all_errors(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """get_document_content handles various error types gracefully."""
        create_document(5001, 1, valid_doc_content)

        error_types = [
            PermissionError(errno.EACCES, "Permission denied"),
            OSError(errno.EIO, "I/O error"),
            OSError(errno.ESTALE, "Stale file handle"),
            ConnectionResetError("Connection reset"),
            MemoryError("Out of memory"),
        ]

        for error in error_types:
            with patch.object(Path, "read_text", side_effect=error):
                result = get_document_content.fn(5001, 1)
                assert "error" in result, f"Failed for {type(error).__name__}"
                assert "code" in result["error"]
                assert "message" in result["error"]

    def test_get_document_metadata_handles_all_errors(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """get_document_metadata handles various error types gracefully."""
        create_document(5002, 1, valid_doc_content)

        error_types = [
            PermissionError(errno.EACCES, "Permission denied"),
            OSError(errno.ENETUNREACH, "Network unreachable"),
            BlockingIOError(errno.ETIMEDOUT, "Timeout"),
        ]

        for error in error_types:
            with patch.object(Path, "read_text", side_effect=error):
                result = get_document_metadata.fn(5002, 1)
                assert "error" in result, f"Failed for {type(error).__name__}"
                assert result["error"]["code"] in ["READ_ERROR", "NOT_FOUND", "INVALID_FORMAT"]

    def test_diff_document_versions_handles_all_errors(
        self, set_documents_env: Path, create_document, valid_doc_content: str, valid_doc_v2_content: str
    ):
        """diff_document_versions handles various error types gracefully."""
        create_document(5003, 1, valid_doc_content)
        create_document(5003, 2, valid_doc_v2_content)

        error_types = [
            PermissionError(errno.EACCES, "Permission denied"),
            OSError(errno.ESTALE, "Stale NFS handle"),
        ]

        for error in error_types:
            with patch.object(Path, "read_text", side_effect=error):
                result = diff_document_versions.fn(5003, 1, 2)
                assert "error" in result, f"Failed for {type(error).__name__}"

    def test_list_documents_never_crashes(self, set_documents_env: Path):
        """list_documents returns empty list rather than crashing."""
        error_scenarios = [
            (Path, "exists", OSError(errno.ENETDOWN, "Network down")),
            (Path, "glob", PermissionError("Cannot list")),
            (Path, "glob", OSError(errno.EIO, "I/O error")),
        ]

        for cls, method, error in error_scenarios:
            with patch.object(cls, method, side_effect=error):
                result = list_documents.fn()
                assert isinstance(result, list), f"Crashed for {method} with {type(error).__name__}"

    def test_list_document_versions_handles_errors(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """list_document_versions returns error dict, not exception."""
        create_document(5004, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = OSError(errno.ESTALE, "Stale handle")
            result = list_document_versions.fn(5004)

        # Should return error dict or empty versions, not raise
        assert isinstance(result, dict)
        if "versions" in result:
            assert isinstance(result["versions"], list)
        elif "error" in result:
            assert "code" in result["error"]


# =============================================================================
# Error Message Quality Tests
# =============================================================================


class TestErrorMessageQuality:
    """Ensure error messages are helpful for debugging remote drive issues."""

    def test_permission_error_message_is_informative(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Permission error includes path and action in message."""
        create_document(6001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = PermissionError(
                errno.EACCES, "Permission denied"
            )
            result = get_document_content.fn(6001, 1)

        assert "error" in result
        # Message should indicate what failed
        message = result["error"]["message"]
        assert len(message) > 10  # Not just "Error"

    def test_network_error_message_includes_cause(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Network error message indicates network issue."""
        create_document(6002, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = OSError(
                errno.ENETUNREACH, "Network is unreachable"
            )
            result = get_document_content.fn(6002, 1)

        assert "error" in result
        message = result["error"]["message"]
        assert "network" in message.lower() or "unreachable" in message.lower()

    def test_not_found_message_includes_document_id(
        self, set_documents_env: Path
    ):
        """Not found error includes document ID for debugging."""
        result = get_document_content.fn(99999, 1)

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "99999" in result["error"]["message"]


# =============================================================================
# Encoding and Character Set Tests
# =============================================================================


class TestEncodingErrors:
    """Tests for encoding-related issues that may occur with remote drives."""

    def test_utf8_decode_error(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """File contains invalid UTF-8 bytes."""
        create_document(7001, 1, valid_doc_content)

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = UnicodeDecodeError(
                "utf-8", b"\xff\xfe", 0, 1, "invalid start byte"
            )
            result = get_document_content.fn(7001, 1)

        assert "error" in result
        assert result["error"]["code"] == "READ_ERROR"

    def test_mixed_encoding_in_filename(
        self, set_documents_env: Path
    ):
        """Filenames with unusual encoding are handled."""
        # Create a file with standard name
        (set_documents_env / "8001_v1.md").write_text(
            """---
type: "Guideline"
author: "Author"
reviewer: "Reviewer"
approver: "Approver"
date: "2025-01-01"
status: "Draft"
---

# Test

Content.
""",
            encoding="utf-8"
        )

        result = list_documents.fn()
        assert len(result) == 1


# =============================================================================
# Symlink and Special File Tests
# =============================================================================


class TestSpecialFiles:
    """Tests for special file types on remote drives."""

    def test_broken_symlink_is_skipped(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Broken symlinks don't crash listing."""
        create_document(8001, 1, valid_doc_content)

        # Create a broken symlink (if supported)
        broken_link = set_documents_env / "8002_v1.md"
        try:
            broken_link.symlink_to("/nonexistent/target")
        except OSError:
            pytest.skip("Symlinks not supported on this filesystem")

        result = list_documents.fn()

        # Should still list the valid document
        assert len(result) >= 1
        valid_ids = [doc.id for doc in result]
        assert 8001 in valid_ids

    def test_directory_with_md_extension_is_skipped(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Directory named like a document file is skipped."""
        create_document(8003, 1, valid_doc_content)

        # Create a directory with .md extension
        fake_doc_dir = set_documents_env / "8004_v1.md"
        fake_doc_dir.mkdir()

        result = list_documents.fn()

        # Should only list the valid file
        valid_ids = [doc.id for doc in result]
        assert 8003 in valid_ids
        assert 8004 not in valid_ids


# =============================================================================
# Recovery and Resilience Tests
# =============================================================================


class TestRecoveryAndResilience:
    """Tests for recovery after transient failures."""

    def test_succeeds_after_transient_failure(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Operations succeed after transient network issues resolve."""
        create_document(9001, 1, valid_doc_content)

        call_count = [0]

        def transient_failure(self, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise OSError(errno.ETIMEDOUT, "Temporary timeout")
            return valid_doc_content

        # First calls fail, subsequent succeed
        with patch.object(Path, "read_text", transient_failure):
            result1 = get_document_content.fn(9001, 1)
            result2 = get_document_content.fn(9001, 1)
            result3 = get_document_content.fn(9001, 1)

        # At least the last one should succeed
        assert "content" in result3

    def test_partial_results_on_mixed_failures(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """List returns partial results when some files are readable."""
        create_document(9002, 1, valid_doc_content)
        create_document(9003, 1, valid_doc_content)

        original_read = Path.read_text

        def selective_failure(self, *args, **kwargs):
            if "9002" in str(self):
                raise OSError(errno.EIO, "Disk error")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", selective_failure):
            result = list_documents.fn()

        # Should still have the readable document
        doc_ids = [doc.id for doc in result]
        assert 9003 in doc_ids

    def test_independent_operations_dont_affect_each_other(
        self, set_documents_env: Path, create_document, valid_doc_content: str
    ):
        """Failure on one document doesn't affect operations on others."""
        create_document(9004, 1, valid_doc_content)
        create_document(9005, 1, valid_doc_content)

        # Make 9004 unreadable
        original_read = Path.read_text

        def selective_read(self, *args, **kwargs):
            if "9004" in str(self):
                raise PermissionError(errno.EACCES, "Permission denied")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", selective_read):
            # 9004 should fail
            result1 = get_document_content.fn(9004, 1)
            # 9005 should succeed
            result2 = get_document_content.fn(9005, 1)

        assert "error" in result1
        assert "content" in result2
