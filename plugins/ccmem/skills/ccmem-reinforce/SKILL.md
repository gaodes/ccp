---
name: ccmem-reinforce
description: Give positive feedback to a memory (+0.1 confidence)
---

# /ccmem-reinforce

Reinforce a memory when it was helpful or correct. Increases confidence by 0.1.

## Usage

```
/ccmem-reinforce <memory-id>
```

## Arguments

- `<memory-id>` — The ID of the memory to reinforce (required)

## Execution Steps

1. Run `ccmem reinforce <memory-id>`
2. Parse the output to get the updated confidence
3. Display result:
   ```
   Reinforced: <title>
   Confidence: <old> → <new>
   ```

## Example

```
User: /ccmem-reinforce 2026-01-29T10-30-00-prefer-pnpm

→ Reinforced: Prefer pnpm for package management
   Confidence: 0.7 → 0.8
```

## Effect

- Confidence increases by 0.1 (capped at 1.0)
- `positive_reinforcement` count increases by 1
- Memory becomes more likely to be applied in future sessions
- At confidence >= 0.8, memory may be synced to CLAUDE.md

## Finding Memory IDs

Use `/ccmem-list` or `/ccmem-search <query>` to find memories.

## CLI Command

```bash
ccmem reinforce <memory-id>
```
