---
name: ccmem-remember
description: Create a memory from natural language or structured flags
---

# /ccmem-remember

Create a new memory to remember user preferences, patterns, or workflows.

## Usage

```
/ccmem-remember <natural language description>
/ccmem-remember --type <type> --title "<title>" [options]
```

## Arguments

The command accepts either natural language or structured flags:

**Natural language:** Parse the input to extract type, title, and description.
```
/ccmem-remember prefer pnpm over npm
/ccmem-remember always run tests before committing
```

**Structured flags:**
- `--type <type>` — preference, pattern, workflow, correction (default: preference)
- `--title "<title>"` — memory title
- `--description "<desc>"` — detailed description
- `--confidence <0.0-1.0>` — initial confidence (default: 0.7)
- `--project` — scope to current project only
- `--tag <tag>` — add a tag (can repeat)

## Execution Steps

1. Parse the input (natural language or flags)
2. For natural language, infer:
   - Type: "prefer" → preference, "always/never" → pattern, "workflow" → workflow
   - Title: Extract the core preference/pattern
   - Description: The full input
3. Run `ccmem create` to create the memory interactively, providing the parsed values
4. Display the created memory with its ID and confidence
5. Suggest: "Use `/ccmem-reinforce <id>` if this works well for you"

## Examples

**Natural language:**
```
User: /ccmem-remember prefer rg over grep for searching
→ Creates preference memory: "Prefer rg over grep for searching"
  ID: 2026-02-03T14-30-00-prefer-rg-over-grep
  Confidence: 0.7
```

**With flags:**
```
User: /ccmem-remember --type workflow --title "Test before commit" --project
→ Creates project-scoped workflow memory
```

## CLI Command

```bash
ccmem create
```

Runs interactively; provide parsed values when prompted.
