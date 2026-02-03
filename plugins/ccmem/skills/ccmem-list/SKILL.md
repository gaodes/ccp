---
name: ccmem-list
description: List memories with optional filters
---

# /ccmem-list

List all active memories, with optional filtering.

## Usage

```
/ccmem-list [options]
```

## Options

- `--project` — Only show memories scoped to current project
- `--global` — Only show global memories
- `--confidence <N>` — Minimum confidence threshold (e.g., 0.5)
- `--type <type>` — Filter by type (preference, pattern, workflow, correction)
- `--tag <tag>` — Filter by tag
- `--limit <N>` — Limit number of results
- `-v` or `--verbose` — Show descriptions

## Execution Steps

1. Build the filter arguments from options
2. Run `ccmem list` with filters
3. Parse output into a table format
4. Display:

**Summary view (default):**
```
ID                                    | Title                    | Conf | Type       | Scope
--------------------------------------|--------------------------|------|------------|--------
2026-01-29T10-30-00-prefer-pnpm       | Prefer pnpm over npm     | 0.85 | preference | global
2026-01-30T14-00-00-test-before-commit| Test before committing   | 0.70 | workflow   | project
```

**Verbose view (-v):**
Includes description snippet for each memory.

## Examples

```
/ccmem-list
→ Shows all active memories

/ccmem-list --project
→ Shows only current project's memories

/ccmem-list --confidence 0.8
→ Shows high-confidence memories only

/ccmem-list --type workflow -v
→ Shows workflow memories with descriptions
```

## CLI Command

```bash
ccmem list [--project] [--global] [--confidence N] [--type TYPE] [--tag TAG] [--limit N]
```
