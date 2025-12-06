# Document Format

Folios uses Markdown files with YAML frontmatter.

## File Naming

Files must follow the pattern `{id}_v{version}.md`:

```
documents/
├── 100001_v1.md    # Document 100001, version 1
├── 100001_v2.md    # Document 100001, version 2 (supersedes v1)
└── 100002_v1.md    # Document 100002, version 1
```

- **ID**: Any positive integer (e.g., 100001, 999999)
- **Version**: Sequential integers starting at 1

## Document Structure

```markdown
---
type: Design Practice
author: John Smith
reviewer: Jane Doe
approver: Bob Wilson
date: 2025-01-15
status: Approved
---

# Document Title

Introduction paragraph...

## First Section

Content...

## Second Section

More content...
```

### YAML Frontmatter

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Document type |
| `author` | Yes | Document author |
| `reviewer` | Yes | Document reviewer |
| `approver` | Yes | Document approver |
| `date` | Yes | Publication date (ISO format) |
| `status` | Yes | Document status |

### Document Body

- **Title**: First `#` heading becomes the document title
- **Chapters**: `##` headings are extracted as chapters
- **Content**: Standard Markdown

## Valid Values

::: folios.server.DocumentType
    options:
      show_root_heading: false
      heading_level: 4


::: folios.server.DocumentStatus
    options:
      show_root_heading: false
      heading_level: 4

## Versioning

- Create new versions by incrementing the version number in the filename
- Keep previous versions (don't delete them)
- Update status to "Withdrawn" when superseded

## Partial Metadata

Documents with missing fields still work but show "NA" for missing values:

```yaml
---
type: Guideline
date: 2025-01-15
status: Draft
# Missing: author, reviewer, approver
---
```
