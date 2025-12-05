# Configuration

## Environment Variable

| Variable | Default | Description |
|----------|---------|-------------|
| `FOLIOS_PATH` | `./documents` | Path to your documents folder |

The path can be:

- Local directory: `/Users/yourname/documents`
- Network share: `/mnt/shared/engineering-docs`
- Relative path: `./documents` (relative to working directory)

## Directory Structure

Folios scans for `*.md` files matching the `{id}_v{version}.md` pattern:

```
documents/
├── 100001_v1.md
├── 100001_v2.md
└── 100002_v1.md
```

Subdirectories are **not** scanned (flat structure only).

## Deployment

### Claude Desktop

See [Home](index.md#claude-desktop) for Claude Desktop configuration.

### VS Code

See [Home](index.md#vs-code-claude-extension) for VS Code configuration.

### Docker

```dockerfile
FROM python:3.12-slim
RUN pip install folios
ENV FOLIOS_PATH=/documents
VOLUME /documents
CMD ["folios"]
```

```bash
docker build -t folios .
docker run -v /path/to/docs:/documents folios
```

## Troubleshooting

### Documents Not Found

1. Check `FOLIOS_PATH` is set correctly
2. Verify files follow the naming pattern: `{id}_v{version}.md`
3. Check file permissions

### Metadata Errors

1. Verify YAML frontmatter has opening and closing `---`
2. Check field values are valid
3. Ensure document has an H1 heading for the title
