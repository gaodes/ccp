---
name: ccmem-promote
description: Interactive review and promotion of high-confidence memories to CLAUDE.md
---

# /ccmem-promote

Review and promote high-confidence memories to your CLAUDE.md file.

## Usage

```
/ccmem-promote
/ccmem-promote --dry-run
```

## Options

- `--dry-run` — Preview candidates without making changes

## Execution Steps

1. Run `ccmem promote --dry-run` to get promotion candidates
2. If no candidates: "No memories ready for promotion (need confidence >= 0.8)"
3. For each candidate, present an interactive review:

### Interactive Review Flow

For each candidate memory:

**Display:**
```
Candidate 1 of 3
================

Title: Prefer pnpm over npm
Type: preference
Confidence: 0.85

Description:
  User consistently chooses pnpm for package management.

Action:
  Suggest pnpm commands instead of npm.

Evidence:
  - Used pnpm 12 times
  - Corrected npm to pnpm 3 times
  - Positive feedback: 2

---
Promote to CLAUDE.md?
  yes  — Add to CLAUDE.md preferences
  no   — Archive this memory
  skip — Leave as-is, continue
  stop — Exit review
```

**Process response:**
- `yes`: Run `ccmem promote` for this memory, continue to next
- `no`: Archive the memory, continue to next
- `skip`: Leave unchanged, continue to next
- `stop`: Exit the review loop

4. After all candidates (or stop):
```
Promotion Summary
=================
Promoted: 2
Archived: 1
Skipped: 0

Your CLAUDE.md has been updated with 2 new preferences.
```

## What Gets Promoted

Memories are formatted and added to the appropriate section in CLAUDE.md:
- Preferences go under `## Preferences`
- Workflows go under `## Workflows`
- Patterns are described in relevant sections

## CLI Commands

```bash
# Preview candidates
ccmem promote --dry-run

# Execute promotion (usually interactive)
ccmem promote
```
