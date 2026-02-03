---
name: ccmem-search
description: Search memories by query
---

# /ccmem-search

Search memories using full-text search.

## Usage

```
/ccmem-search <query> [options]
```

## Arguments

- `<query>` — Search terms (required)

## Options

- `--limit <N>` — Maximum results (default: 10)
- `--project` — Search only current project
- `--global` — Search only global memories

## Execution Steps

1. Run `ccmem search "<query>"` with options
2. Parse results
3. Display matches with relevance highlighting

## Output

```
Search: "pnpm"

Found 3 memories:

1. 2026-01-29T10-30-00-prefer-pnpm (confidence: 0.85)
   Title: Prefer pnpm over npm
   Match: "...always use **pnpm** for Node.js projects..."

2. 2026-01-30T09-00-00-pnpm-workspace (confidence: 0.70)
   Title: Use pnpm workspaces for monorepos
   Match: "...configure **pnpm** workspace in pnpm-workspace.yaml..."

3. 2026-02-01T11-00-00-pnpm-install (confidence: 0.60)
   Title: Run pnpm install after checkout
   Match: "...run **pnpm** install when switching branches..."
```

## Tips

- Use `/ccmem-show <id>` to see full details of a match
- Use `/ccmem-reinforce <id>` if a search result is what you wanted
- Search looks in title, description, action, and tags

## CLI Command

```bash
ccmem search "<query>" [--limit N] [--project] [--global]
```
