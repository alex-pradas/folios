# Folios Project Memory

## Release Process

Use the `/release` slash command for releases. It handles:

1. **Documentation validation** - Ensures doc examples match actual tool outputs
2. **Version updates** - Bumps version in pyproject.toml and docs
3. **Changelog** - Drafts entry and asks for user confirmation before proceeding
4. **Tests** - Runs pytest to verify everything passes
5. **Release** - Commits, pushes, and creates GitHub release

The CI workflow (`.github/workflows/publish.yml`) automatically publishes to PyPI when a release is published.

Do NOT use `uv publish` directly - use GitHub releases to trigger the CI pipeline.
