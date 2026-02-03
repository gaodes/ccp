---
name: ccmem-stats
description: Show overall memory system statistics
---

# /ccmem-stats

Display statistics about the ccmem memory system.

## Usage

```
/ccmem-stats
```

## Execution Steps

1. Run `ccmem stats`
2. Parse and reformat the output for conversation
3. Display statistics in a readable format

## Output

```
ccmem Statistics
================

Memories: 23 total
  - Active: 18
  - Under review: 3
  - Archived: 2

By type:
  - Preferences: 12
  - Patterns: 6
  - Workflows: 4
  - Corrections: 1

By confidence:
  - High (≥0.8): 8
  - Medium (0.5-0.8): 7
  - Low (<0.5): 3

Observations: 1,247 total
Sessions: 42

Last analysis: 2 days ago
Last maintenance: 1 day ago
```

## CLI Command

```bash
ccmem stats
```
