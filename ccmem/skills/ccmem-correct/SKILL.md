---
name: ccmem-correct
description: Give negative feedback to a memory (-0.2 confidence)
---

# /ccmem-correct

Correct a memory when it was wrong or outdated. Decreases confidence by 0.2.

## Usage

```
/ccmem-correct <memory-id>
```

## Arguments

- `<memory-id>` — The ID of the memory to correct (required)

## Execution Steps

1. Run `ccmem correct <memory-id>`
2. Parse the output to get the updated confidence
3. Display result:
   ```
   Corrected: <title>
   Confidence: <old> → <new>
   ```
4. Ask: "Would you like to create a replacement memory? (yes/no)"
5. If yes, prompt for the correct preference and use `/ccmem-remember` flow

## Example

```
User: /ccmem-correct 2026-01-29T10-30-00-prefer-npm

→ Corrected: Prefer npm for package management
   Confidence: 0.6 → 0.4

   Would you like to create a replacement memory?

User: yes, I now prefer pnpm

→ [Creates new memory via ccmem-remember flow]
```

## Effect

- Confidence decreases by 0.2 (minimum 0.0)
- `negative_reinforcement` count increases by 1
- If confidence drops below 0.3: status changes to "under_review"
- If confidence drops below 0.1: status changes to "archived"

## Finding Memory IDs

Use `/ccmem-list` or `/ccmem-search <query>` to find memories.

## CLI Command

```bash
ccmem correct <memory-id>
```
