---
name: memory-create
description: Create and manage memory files for the file-based memory system
---

# Memory Create Skill

Create, update, and manage memory files in `~/.claude/memory/memories/`.

## Available Functions

### Create New Memory

```python
from memory_lib import create_memory

memory = create_memory(
    type="preference",
    scope_type="global",
    scope_path=None,
    content={
        "title": "Prefer pnpm over npm",
        "description": "User consistently uses pnpm",
        "action": "Suggest pnpm when discussing packages",
        "examples": ["pnpm install"]
    },
    triggers={
        "description": "when discussing package management",
        "keywords": ["npm", "install"],
        "patterns": ["npm install"],
        "files": ["package.json"]
    },
    tags=["tooling", "javascript"],
    evidence=[{
        "timestamp": "2026-01-29T03:00:00Z",
        "observation_id": "obs-123",
        "description": "User used pnpm install"
    }],
    confidence=0.85
)
```

### Update Existing Memory

```python
from memory_lib import update_memory

update_memory(
    memory_id="2026-01-29-pnpm-preference",
    new_evidence={
        "timestamp": "2026-01-30T10:00:00Z",
        "description": "User rejected npm suggestion"
    },
    confidence_delta=0.05
)
```

### Build Search Index

```python
from memory_lib import build_search_index

build_search_index()
```

## Memory Type Reference

| Type | Use Case | Example |
|------|----------|---------|
| preference | User likes/dislikes | "Prefer pnpm" |
| pattern | Code patterns | "Use early returns" |
| correction | Learned from mistakes | "User prefers Zod" |
| project | Project-specific | "This uses Vitest" |
| negative | What NOT to do | "Never use MD5" |
| workflow | Processes | "Run tests first" |

## File Locations

- Global memories: `~/.claude/memory/memories/global/{id}.json`
- Project memories: `~/.claude/memory/memories/projects/{hash}/{id}.json`

## Example: Creating a Memory from Analysis

```python
import json
from datetime import datetime
from memory_lib import create_memory, get_project_hash

# Detected pattern from observations
pattern = {
    "tool": "pnpm",
    "alternative": "npm",
    "occurrences": 5,
    "evidence": [...]
}

# Create memory
memory_id = create_memory(
    type="preference",
    scope_type="global",
    content={
        "title": f"Prefer {pattern['tool']} over {pattern['alternative']}",
        "description": f"User consistently uses {pattern['tool']}",
        "action": f"Suggest {pattern['tool']} for package management",
        "examples": [f"{pattern['tool']} install"]
    },
    triggers={
        "keywords": [pattern['alternative'], "install", "package"],
        "patterns": [f"{pattern['alternative']} install"]
    },
    tags=["tooling", "javascript", "package-management"],
    evidence=pattern["evidence"],
    confidence=min(0.5 + (pattern["occurrences"] * 0.1), 0.95)
)

print(f"Created memory: {memory_id}")
```
