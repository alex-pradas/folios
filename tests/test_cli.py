"""Tests for CLI entry point and configuration."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import folios.server as server_module
from folios.server import get_documents_path, main


class TestGetDocumentsPath:
    """Tests for get_documents_path configuration priority."""

    def test_cli_path_takes_priority_over_env(self, tmp_path: Path, monkeypatch):
        """CLI path should be returned when set, even if env var exists."""
        cli_path = tmp_path / "cli_docs"
        env_path = tmp_path / "env_docs"
        cli_path.mkdir()
        env_path.mkdir()

        # Set both CLI and env var
        monkeypatch.setattr(server_module, "_cli_folios_path", cli_path)
        monkeypatch.setenv("FOLIOS_PATH", str(env_path))

        result = get_documents_path()

        assert result == cli_path

    def test_raises_runtime_error_when_no_path_configured(self, monkeypatch):
        """RuntimeError raised when neither CLI nor env var is set."""
        monkeypatch.setattr(server_module, "_cli_folios_path", None)
        monkeypatch.delenv("FOLIOS_PATH", raising=False)

        with pytest.raises(RuntimeError, match="No documents path configured"):
            get_documents_path()


class TestMain:
    """Tests for the CLI main() entry point."""

    def test_main_with_folios_path_argument(self, tmp_path: Path, monkeypatch):
        """main() should set _cli_folios_path when --folios-path is provided."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()

        monkeypatch.setattr(server_module, "_cli_folios_path", None)
        monkeypatch.delenv("FOLIOS_PATH", raising=False)
        monkeypatch.setattr(sys, "argv", ["folios", "--folios-path", str(docs_path)])

        # Mock server.run to prevent actual server startup
        with patch.object(server_module.server, "run") as mock_run:
            main()

        assert server_module._cli_folios_path == docs_path
        mock_run.assert_called_once_with(show_banner=False)

    def test_main_with_env_var_only(self, tmp_path: Path, monkeypatch):
        """main() should work with just FOLIOS_PATH env var."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()

        monkeypatch.setattr(server_module, "_cli_folios_path", None)
        monkeypatch.setenv("FOLIOS_PATH", str(docs_path))
        monkeypatch.setattr(sys, "argv", ["folios"])

        with patch.object(server_module.server, "run") as mock_run:
            main()

        mock_run.assert_called_once_with(show_banner=False)

    def test_main_exits_with_error_when_no_path(self, monkeypatch, capsys):
        """main() should exit with error when no path is configured."""
        monkeypatch.setattr(server_module, "_cli_folios_path", None)
        monkeypatch.delenv("FOLIOS_PATH", raising=False)
        monkeypatch.setattr(sys, "argv", ["folios"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: No documents folder specified" in captured.err
        assert "--folios-path" in captured.err
        assert "FOLIOS_PATH" in captured.err
