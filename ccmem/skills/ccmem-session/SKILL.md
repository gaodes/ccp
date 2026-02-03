---
name: ccmem-session
description: Show what ccmem captured in this session
---

# /ccmem-session

Display what ccmem has captured during the current session.

## Usage

```
/ccmem-session [-v]
```

## Options

- `-v` or `--verbose` — Show full details of observations

## Execution Steps

1. Find the current session ID from `~/.claude/memory/sessions.json`
2. Read observations from `~/.claude/memory/observations.jsonl` for this session
3. Count observations by type (prompt, tool, file)
4. Check for any patterns detected or memories created this session
5. Display summary or verbose output

## Output

**Summary view (default):**
```
Session: abc123def (started 2h ago)

Observations: 47
  - Prompts: 32
  - Tool uses: 12
  - File changes: 3

Patterns detected: 2
Memories created: 1
```

**Verbose view (-v):**
```
Session: abc123def (started 2h ago)

Recent observations:
  [14:30] prompt: "Let's add error handling..."
  [14:31] tool: Edit on src/utils.ts
  [14:32] tool: Bash running tests
  ...

Patterns detected:
  - Tool preference: rg over grep (3 occurrences)
  - Workflow: test after edit (2 occurrences)

Memories created:
  - 2026-02-03T14-35-00-prefer-rg: Prefer rg for searching
```

## Data Locations

```bash
# Session info
~/.claude/memory/sessions.json

# Observations
~/.claude/memory/observations.jsonl
```
