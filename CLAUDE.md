# Folios Project Memory

## Release Process

When the user says "ready to release" or "release vX.Y.Z", follow these steps systematically:

1. **Check git log** for changes since last release
2. **Bump version** in `pyproject.toml`
3. **Update CHANGELOG.md** with new section following Keep a Changelog format:
   - Added, Changed, Fixed, Removed sections as needed
   - Date in YYYY-MM-DD format
4. **Run tests** via `uv run pytest` to verify everything passes
5. **Commit** all changes with message: `v{version}: {brief summary}`
6. **Push** to main
7. **Create GitHub release** via `gh release create v{version}` with release notes
   - This automatically creates the git tag and triggers PyPI publish

The CI workflow (`.github/workflows/publish.yml`) automatically publishes to PyPI when a release is published.

Do NOT use `uv publish` directly - use GitHub releases to trigger the CI pipeline.
