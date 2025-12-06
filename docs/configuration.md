# Configuration

Folios works out of the box with zero configuration. Just point it at a folder of Markdown files and go. However, you can optionally configure field definitions to help AI agents better understand and query your documents.

## Why Configure?

When an AI agent uses Folios tools, it needs to know what values are valid for filtering. Without configuration:

- The agent must guess or ask what document types exist
- Filter suggestions may not match your actual data
- The agent can't validate its queries against known values

With configuration:

- Tool descriptions include valid values for each field
- Agents can make more accurate queries immediately
- Better autocomplete and validation in MCP-compatible clients

## Configuration File

Create a `folios.toml` file in your documents folder:

```
documents/
├── folios.toml          # Configuration file
├── 100001_v1.md
├── 100001_v2.md
└── 100002_v1.md
```

## Format

Define allowed values for any frontmatter field:

```toml
# folios.toml

[fields.status]
values = ["Draft", "In Review", "Approved", "Withdrawn"]

[fields.document_type]
values = ["Design Practice", "Guideline", "Best Practice", "TRS", "DVP", "DVR"]

[fields.department]
values = ["Engineering", "Manufacturing", "HR", "Finance"]
```

## How It Works

When Folios starts, it reads `folios.toml` and includes the allowed values in the MCP tool descriptions. For example, the `list_documents` tool description will show:

```
Filter by status (Draft|In Review|Approved|Withdrawn)
Filter by document_type (Design Practice|Guideline|Best Practice|TRS|DVP|DVR)
```

This helps AI agents understand what values they can use when querying your document library.

## Example

Given this configuration:

```toml
[fields.status]
values = ["Draft", "Approved"]

[fields.document_type]
values = ["Guideline", "TRS"]
```

An AI agent can confidently query:

```
list_documents(status="Approved", document_type="TRS")
```

Without configuration, the agent would need to either guess these values or ask you first.

## Notes

- Configuration is entirely optional
- Documents with values not in the config are still accepted
- The config only affects tool descriptions, not validation
- Changes to `folios.toml` require restarting the server
