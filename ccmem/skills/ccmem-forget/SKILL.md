---
name: ccmem-forget
description: Archive a memory by ID (with confirmation)
---

# /ccmem-forget

Archive a memory so it no longer affects behavior.

## Usage

```
/ccmem-forget <memory-id>
```

## Arguments

- `<memory-id>` — The ID of the memory to archive (required)

## Execution Steps

1. Run `ccmem show <memory-id>` to display the memory
2. If memory not found, report error
3. Show the memory details to the user
4. Ask for confirmation: "Archive this memory? It will no longer affect behavior. (yes/no)"
5. If confirmed:
   - The memory will be archived (status set to "archived", confidence set to 0)
   - Run appropriate ccmem command or update the memory file directly
6. Confirm: "Memory archived: <id>"

## Example

```
User: /ccmem-forget 2026-01-29T10-30-00-prefer-npm

→ Showing memory:
  Title: Prefer npm for package management
  Type: preference
  Confidence: 0.65

  Archive this memory? (yes/no)

User: yes

→ Memory archived: 2026-01-29T10-30-00-prefer-npm
```

## Finding Memory IDs

Use `/ccmem-list` to see all memories with their IDs.

## CLI Commands

```bash
# Show the memory first
ccmem show <memory-id>

# To archive, update the memory file:
# Set metadata.status = "archived" and metadata.confidence = 0
```
