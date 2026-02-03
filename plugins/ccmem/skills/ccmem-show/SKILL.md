---
name: ccmem-show
description: Display full details of a specific memory
---

# /ccmem-show

Show complete details of a memory.

## Usage

```
/ccmem-show <memory-id>
```

## Arguments

- `<memory-id>` — The ID of the memory to display (required)

## Execution Steps

1. Run `ccmem show <memory-id>`
2. Parse the output
3. Display in a readable format
4. Offer suggested actions

## Output

```
Memory: 2026-01-29T10-30-00-prefer-pnpm
========================================

Title: Prefer pnpm over npm
Type: preference
Scope: global
Status: active

Description:
  User consistently chooses pnpm for package management in Node.js projects.

Action:
  Suggest pnpm commands instead of npm. Use pnpm add, pnpm install, pnpm run.

Examples:
  - "pnpm add lodash" instead of "npm install lodash"
  - "pnpm run build" instead of "npm run build"

Confidence: 0.85
  - Positive feedback: 3
  - Negative feedback: 0

Created: 2026-01-29T10:30:00Z
Last accessed: 2026-02-03T09:15:00Z
Access count: 12

Tags: tools, package-manager, nodejs

Evidence (3 observations):
  - 2026-01-29: Used pnpm add in project A
  - 2026-01-30: Corrected npm to pnpm
  - 2026-02-01: Used pnpm workspace

---
Actions:
  /ccmem-reinforce 2026-01-29T10-30-00-prefer-pnpm  — if this is helpful
  /ccmem-correct 2026-01-29T10-30-00-prefer-pnpm    — if this is wrong
  /ccmem-forget 2026-01-29T10-30-00-prefer-pnpm     — to archive
```

## CLI Command

```bash
ccmem show <memory-id>
```
