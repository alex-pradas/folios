"""Tests for CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from folios.server import main


class TestMain:
    """Tests for the CLI main() entry point."""

    def test_main_with_path_argument(self, documents_path: Path, monkeypatch):
        """main() should create server with provided --path."""
        monkeypatch.delenv("FOLIOS_PATH", raising=False)
        monkeypatch.setattr(sys, "argv", ["folios", "--path", str(documents_path)])

        # Mock create_server and server.run to prevent actual server startup
        with patch("folios.server.create_server") as mock_create:
            mock_server = MagicMock()
            mock_create.return_value = mock_server

            main()

            # Verify create_server was called with the right path
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] == documents_path  # First positional arg is docs_path
            mock_server.run.assert_called_once_with(show_banner=False)

    def test_main_with_env_var_only(self, documents_path: Path, monkeypatch):
        """main() should work with just FOLIOS_PATH env var."""
        monkeypatch.setenv("FOLIOS_PATH", str(documents_path))
        monkeypatch.setattr(sys, "argv", ["folios"])

        with patch("folios.server.create_server") as mock_create:
            mock_server = MagicMock()
            mock_create.return_value = mock_server

            main()

            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] == documents_path
            mock_server.run.assert_called_once_with(show_banner=False)

    def test_main_exits_with_error_when_no_path(self, monkeypatch, capsys):
        """main() should exit with error when no path is configured."""
        monkeypatch.delenv("FOLIOS_PATH", raising=False)
        monkeypatch.setattr(sys, "argv", ["folios"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: No documents folder specified" in captured.err
        assert "--path" in captured.err
        assert "FOLIOS_PATH" in captured.err

    def test_cli_path_takes_priority_over_env(self, tmp_path: Path, monkeypatch):
        """CLI path should be used when both CLI and env var are set."""
        cli_path = tmp_path / "cli_docs"
        env_path = tmp_path / "env_docs"
        cli_path.mkdir()
        env_path.mkdir()

        monkeypatch.setenv("FOLIOS_PATH", str(env_path))
        monkeypatch.setattr(sys, "argv", ["folios", "--path", str(cli_path)])

        with patch("folios.server.create_server") as mock_create:
            mock_server = MagicMock()
            mock_create.return_value = mock_server

            main()

            # Should use CLI path, not env path
            call_args = mock_create.call_args
            assert call_args[0][0] == cli_path
