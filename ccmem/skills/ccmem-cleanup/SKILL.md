---
name: ccmem-cleanup
description: Review and clean up low-confidence memories
---

# /ccmem-cleanup

Review low-confidence memories and decide whether to archive or reinforce them.

## Usage

```
/ccmem-cleanup
/ccmem-cleanup --threshold 0.4
```

## Options

- `--threshold <N>` — Confidence threshold (default: 0.3). Memories below this are reviewed.

## Execution Steps

1. Find all memories with confidence below threshold
2. If none: "No low-confidence memories to review"
3. For each memory, present an interactive review:

### Interactive Review Flow

For each low-confidence memory:

**Display:**
```
Review 1 of 5 (confidence < 0.3)
================================

Title: Prefer tabs over spaces
Type: preference
Confidence: 0.25
Status: under_review

Description:
  User mentioned preferring tabs in one conversation.

Last accessed: 30 days ago
Feedback: 0 positive, 1 negative

---
What would you like to do?
  archive   — Remove from active memories
  reinforce — Boost confidence (+0.1)
  skip      — Leave as-is
  stop      — Exit review
```

**Process response:**
- `archive`: Set status to archived, continue
- `reinforce`: Run `ccmem reinforce <id>`, continue
- `skip`: Leave unchanged, continue
- `stop`: Exit the review loop

4. After all memories (or stop):
```
Cleanup Summary
===============
Archived: 3
Reinforced: 1
Skipped: 1

Active memories: 15 (was 18)
```

## When to Run

- After `ccmem stats` shows many low-confidence memories
- Periodically to prune stale preferences
- When memories seem outdated or wrong

## Related Commands

- `/ccmem-list --confidence 0.3` — See low-confidence memories
- `/ccmem-forget <id>` — Archive a specific memory
- `/ccmem-reinforce <id>` — Boost a specific memory
