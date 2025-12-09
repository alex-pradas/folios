# Folios Project Memory

## Release to PyPI

To release a new version to PyPI:

1. Bump version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit and push to main
4. Create a GitHub release via `gh release create v{version}`

The CI workflow (`.github/workflows/publish.yml`) automatically publishes to PyPI when a release is published.

Do NOT use `uv publish` directly - use GitHub releases to trigger the CI pipeline.
