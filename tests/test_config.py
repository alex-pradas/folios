"""Tests for configuration loading from folios.toml."""

import pytest
from pathlib import Path

from folios.server import (
    load_config,
    get_field_values,
    reset_config_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset config cache before and after each test."""
    reset_config_cache()
    yield
    reset_config_cache()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_returns_none_when_no_config_file(self, set_documents_env: Path):
        """Returns None when folios.toml doesn't exist."""
        result = load_config()
        assert result is None

    def test_loads_config_from_toml(self, set_documents_env: Path):
        """Loads configuration from folios.toml."""
        config_content = """
[fields.status]
values = ["Draft", "In Review", "Approved"]

[fields.type]
values = ["Guideline", "Design Practice"]
"""
        (set_documents_env / "folios.toml").write_text(config_content)

        result = load_config()

        assert result is not None
        assert "fields" in result
        assert result["fields"]["status"]["values"] == ["Draft", "In Review", "Approved"]
        assert result["fields"]["type"]["values"] == ["Guideline", "Design Practice"]

    def test_caches_config_on_subsequent_calls(self, set_documents_env: Path):
        """Config is cached after first load."""
        config_content = """
[fields.status]
values = ["Draft"]
"""
        config_path = set_documents_env / "folios.toml"
        config_path.write_text(config_content)

        # First call loads config
        result1 = load_config()
        assert result1["fields"]["status"]["values"] == ["Draft"]

        # Modify file
        config_path.write_text('[fields.status]\nvalues = ["Changed"]')

        # Second call returns cached value
        result2 = load_config()
        assert result2["fields"]["status"]["values"] == ["Draft"]  # Still old value

    def test_returns_none_when_no_documents_path(self, monkeypatch):
        """Returns None when documents path is not configured."""
        monkeypatch.delenv("FOLIOS_PATH", raising=False)

        result = load_config()
        assert result is None

    def test_handles_invalid_toml_gracefully(self, set_documents_env: Path):
        """Invalid TOML syntax is handled gracefully."""
        (set_documents_env / "folios.toml").write_text("invalid [ toml syntax")

        with pytest.raises(Exception):  # tomllib.TOMLDecodeError
            load_config()


class TestGetFieldValues:
    """Tests for get_field_values function."""

    def test_returns_none_when_no_config(self, set_documents_env: Path):
        """Returns None when no config file exists."""
        result = get_field_values("status")
        assert result is None

    def test_returns_none_when_field_not_configured(self, set_documents_env: Path):
        """Returns None when field is not in config."""
        config_content = """
[fields.status]
values = ["Draft"]
"""
        (set_documents_env / "folios.toml").write_text(config_content)

        result = get_field_values("nonexistent")
        assert result is None

    def test_returns_values_for_configured_field(self, set_documents_env: Path):
        """Returns values list for configured field."""
        config_content = """
[fields.status]
values = ["Draft", "In Review", "Approved", "Withdrawn"]

[fields.department]
values = ["Engineering", "HR", "Finance"]
"""
        (set_documents_env / "folios.toml").write_text(config_content)

        status_values = get_field_values("status")
        assert status_values == ["Draft", "In Review", "Approved", "Withdrawn"]

        dept_values = get_field_values("department")
        assert dept_values == ["Engineering", "HR", "Finance"]

    def test_returns_none_when_values_key_missing(self, set_documents_env: Path):
        """Returns None when field config doesn't have 'values' key."""
        config_content = """
[fields.status]
description = "Document status"
"""
        (set_documents_env / "folios.toml").write_text(config_content)

        result = get_field_values("status")
        assert result is None


class TestResetConfigCache:
    """Tests for reset_config_cache function."""

    def test_clears_cached_config(self, set_documents_env: Path):
        """Reset allows reloading config from file."""
        config_path = set_documents_env / "folios.toml"
        config_path.write_text('[fields.status]\nvalues = ["Original"]')

        # Load initial config
        result1 = load_config()
        assert result1["fields"]["status"]["values"] == ["Original"]

        # Modify file and reset cache
        config_path.write_text('[fields.status]\nvalues = ["Updated"]')
        reset_config_cache()

        # Now loads new value
        result2 = load_config()
        assert result2["fields"]["status"]["values"] == ["Updated"]
