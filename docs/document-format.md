# Document Format

Folios uses Markdown files with optional YAML frontmatter. This page explains what's required, what's optional, and how metadata flows into tool responses.

## Minimum Requirements

To work with Folios, a document needs only two things:

1. **Filename**: Must follow the pattern `{id}_v{version}.md`
2. **H1 Title**: The first `#` heading becomes the document title

That's it. The simplest valid document:

```markdown
# My Document

Content here.
```

Frontmatter is entirely optional. But, if you don't include it, `author` and `date` will show as "NA" in responses. This is because the tools that return metadata always include these fields.

In addition, you can add any other fields you want to the frontmatter. See "Adding Custom Fields" below.

## File Naming

Files must follow the pattern `{id}_v{version}.md`:

```
documents/
├── 100001_v1.md    # Document 100001, version 1
├── 100001_v2.md    # Document 100001, version 2
└── 100002_v1.md    # Document 100002, version 1
```

- **ID**: Any positive integer (e.g., 100001, 999999)
- **Version**: Sequential integers starting at 1

## Metadata in Tool Responses

When you call `get_document_metadata` or `browse_catalog`, Folios returns structured metadata. Some fields are always present:

| Field | Source | Default |
|-------|--------|---------|
| `id` | Filename | — |
| `version` | Filename | — |
| `title` | First H1 heading | — |
| `author` | Frontmatter | "NA" |
| `date` | Frontmatter | "NA" |
| `chapters` | H2 headings | [] |

If `author` or `date` are missing from the frontmatter, they show as "NA" in responses.

## Adding Custom Fields

Any field you add to the frontmatter is included in metadata responses:

```markdown
---
author: "J. Smith"
date: "2025-01-15"
status: "Approved"
department: "Engineering"
priority: "High"
---

# Document Title

Content...
```

See [Configuration](configuration.md) to help agents discover valid field values.

All these fields (`author`, `date`, `status`, `department`, `priority`) appear in the metadata response.

## Chapters

H2 headings (`##`) are automatically extracted as chapters:

```markdown
# Document Title

Introduction...

## Background

Content...

## Methodology

Content...
```

This produces `chapters: [{"title": "Background"}, {"title": "Methodology"}]`.

## Versioning

- Create new versions by incrementing the version number in the filename
- Keep previous versions for history (don't delete them)
- Consider updating `status` to "Withdrawn" when superseded

## Complete Example

A fully-featured document:

```markdown
---
author: "J. Smith"
date: "2025-01-15"
document_type: "Design Practice"
status: "Approved"
reviewer: "A. Johnson"
approver: "M. Williams"
---

# Stress Analysis Design Practice

This document defines the standard approach for stress analysis.

## Scope

Applies to all structural components.

## Methodology

Step-by-step process...

## References

Related documents...
```

## Next Steps

- See [Configuration](configuration.md) to define valid values for fields like `status` and `document_type`
- See [API Reference](api-reference.md) for complete tool documentation
