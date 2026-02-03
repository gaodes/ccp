# ccmem - Build Guide

This document teaches agents how to build, extend, and maintain the file-based memory system.

## System Overview

The memory system is a zero-dependency, file-based learning system that:

1. Captures session events via Claude Code hooks
2. Stores observations in append-only JSONL files
3. Detects patterns and creates structured JSON memories
4. Provides full-text search without external databases
5. Learns from feedback via confidence adjustment

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SESSION                       │
├─────────────────────────────────────────────────────────────┤
│  Hooks (capture.sh)                                         │
│  ├── SessionStart → observations.jsonl                      │
│  ├── UserPromptSubmit → observations.jsonl                  │
│  ├── PostToolUse → observations.jsonl                       │
│  └── Stop → finalize session                                │
├─────────────────────────────────────────────────────────────┤
│  Session Context (loaded at start)                          │
│  ├── Global memories (all)                                  │
│  ├── Project memories (current project)                     │
│  ├── Recent memories (last 7 days)                          │
│  └── High-confidence (auto-apply)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKGROUND ANALYZER (spawned)               │
├─────────────────────────────────────────────────────────────┤
│  Pattern Detection                                           │
│  ├── Read observations.jsonl                                │
│  ├── Detect patterns                                        │
│  ├── Create/update memories                                 │
│  ├── Update search-index.json                               │
│  └── Archive processed observations                         │
└─────────────────────────────────────────────────────────────┘
```

## Plugin Structure

ccmem is packaged as a Claude Code plugin:

```
ccmem/
├── .claude-plugin/              # Plugin manifests (required)
│   ├── plugin.json              # Plugin manifest
│   └── marketplace.json         # Dev marketplace
├── hooks/                       # Claude Code hooks
│   ├── on-start.sh              # Session start + recovery
│   ├── capture.sh               # Event capture
│   ├── on-stop.sh               # Session finalization
│   └── promote-candidates.sh    # CLAUDE.md sync trigger
├── scripts/                     # Python utilities
│   ├── lib/memory_lib.py        # Core library
│   ├── build-index.py           # Search index builder
│   ├── update-confidence.py     # Confidence adjustment
│   ├── maintenance.sh           # Periodic maintenance
│   ├── project-detect.sh        # Project detection
│   ├── sync-claude-md.py        # CLAUDE.md sync
│   └── promote-workflow.py      # Promotion workflow
├── skills/                      # Claude Code skills
│   ├── memory-create/SKILL.md
│   ├── memory-retrieve/SKILL.md
│   └── memory-feedback/SKILL.md
├── agents/                      # Agent instructions
│   └── analyzer.md              # Pattern detection agent
├── bin/                         # CLI commands
│   ├── ccmem                    # Main CLI
│   └── memory                   # Extended wrapper script
├── automation/                  # macOS launch agent
│   └── com.elche.memory-maintenance.plist
├── docs/                        # Additional documentation
│   └── MIGRATION.md
├── README.md                    # User documentation
└── BUILD.md                     # Build guide (you are here)
```

### Runtime Data Directory

When running, ccmem stores data in:

```
~/.claude/memory/              # Default location (configurable)
├── config.json                # System configuration
├── index.json                 # Master memory index
├── sessions.json              # Session history
├── observations.jsonl         # Event stream (append-only)
├── observations.archive.jsonl # Rotated observations
├── feedback.jsonl             # User feedback log
├── search-index.json          # Full-text search index
├── memories/                  # Memory storage
│   ├── global/                # Global memories (*.json)
│   └── projects/{hash}/       # Per-project memories
└── logs/                      # Maintenance logs
```

Set `CLAUDE_MEMORY_DIR` environment variable to change the data location.

## Plugin Development

### Testing Changes

When developing ccmem as a plugin:

```bash
# 1. Make changes to plugin files
# 2. Uninstall the plugin
/plugin uninstall ccmem@ccmem-dev

# 3. Reinstall to pick up changes
/plugin install ccmem@ccmem-dev

# 4. Restart Claude Code to reload
```

### Plugin Components

The plugin exposes these components via `.claude-plugin/plugin.json`:

**Hooks:**
- `ccmem-session-start` - Fires on SessionStart, initializes session
- `ccmem-prompt-capture` - Fires on UserPromptSubmit, captures prompts
- `ccmem-tool-capture` - Fires on PostToolUse, captures tool usage
- `ccmem-session-stop` - Fires on Stop, finalizes session

**Skills:**
- `memory-create` - How to create and manage memories
- `memory-retrieve` - How to load and search memories
- `memory-feedback` - How to provide feedback on memories

**Commands:**
- `/ccmem` - CLI access to all memory system functions

### Environment Configuration

The plugin respects the `CLAUDE_MEMORY_DIR` environment variable:

```bash
# Default location
~/.claude/memory/

# Custom location
export CLAUDE_MEMORY_DIR="/path/to/custom/memory"
```

## Build Instructions

### Prerequisites

- macOS or Linux
- `bash` 4.0+
- `jq` (JSON processor)
- `python3` 3.8+
- Claude Code with hook support

### Step 1: Create Directory Structure

```bash
mkdir -p ~/.claude/memory/{hooks,scripts/lib,skills,agents,bin,memories/{global,projects},logs,exports}
```

### Step 2: Core Configuration Files

**config.json** - System identity and settings:

```json
{
  "version": "1.0.0",
  "created_at": "2026-01-01T00:00:00Z",
  "identity": {
    "name": "Personal Memory System",
    "session_count": 0,
    "total_observations": 0,
    "total_memories": 0
  },
  "settings": {
    "observation_limit": 100000,
    "archive_threshold": 50000,
    "confidence_decay_days": 30,
    "min_confidence": 0.1,
    "auto_promote_threshold": 0.8,
    "project_detection": "git_root",
    "max_prompt_length": 500,
    "max_command_length": 200
  },
  "last_session": null,
  "last_analysis": null,
  "last_maintenance": null
}
```

**index.json** - Master memory index:

```json
{
  "version": "1.0.0",
  "updated_at": "2026-01-01T00:00:00Z",
  "memories": {
    "global": [],
    "projects": {}
  },
  "stats": {
    "global_count": 0,
    "project_count": 0,
    "total_count": 0
  }
}
```

**sessions.json** - Session history:

```json
{
  "sessions": [],
  "total_sessions": 0
}
```

**feedback.jsonl** - Feedback log (with schema comment):

```
# Feedback Schema: {timestamp, session_id, memory_id, type, feedback, outcome, auto_creates_memory}
```

### Step 3: Core Library (memory_lib.py)

The core library provides:

- `create_memory()` - Create new memory files
- `load_memory()` - Load memory by ID
- `update_memory()` - Update existing memories
- `search_memories()` - Full-text search
- `log_feedback()` - Log user feedback
- `create_correction_memory()` - Create correction memories
- `build_search_index()` - Build inverted index
- `load_session_context()` - Load session context

Key implementation details:

- All memories are JSON files
- Memories stored in `memories/global/` or `memories/projects/{hash}/`
- IDs follow format: `{YYYY-MM-DDTHH-MM-SS}-{kebab-description}`
- Index is updated atomically using temp files

### Step 4: Hook Scripts

**on-start.sh**:

1. Recover orphaned sessions (crash recovery)
2. Generate session ID
3. Detect project path (git root)
4. Write `session_start` observation
5. Update `config.json`
6. Trigger CLAUDE.md sync (promote high-confidence memories)

**capture.sh**:

- Capture prompts, tool uses, file modifications
- Truncate long content
- Write to `observations.jsonl`

**on-stop.sh**:

1. Calculate session duration
2. Count observations
3. Write `session_end` observation
4. Update `sessions.json`
5. Update `config.json`

### Step 5: Utility Scripts

**build-index.py**:

- Reads all memory files
- Builds inverted index (terms → memory IDs)
- Indexes tags separately
- Outputs `search-index.json`

**update-confidence.py**:

- `adjust_confidence()` - Apply feedback outcomes
- `apply_confidence_decay()` - Time-based decay
- `process_pending_feedback()` - Process `feedback.jsonl`

**maintenance.sh**:

- Orchestrates all maintenance tasks
- Runs: feedback processing → decay → archiving → index rebuild
- Updates `last_maintenance` timestamp

**sync-claude-md.py**:

- **Promote** (`--promote`): High-confidence memories (≥0.8) → CLAUDE.md
- **Import** (`--import`): CLAUDE.md rules → memories (0.6 confidence)
- **Two-way sync** (`--sync`): Import then promote
- Uses HTML comments as markers: `<!-- memory-sync: start/end -->`
- Preserves manual content outside sync markers
- Automatically triggered by `on-start.sh` hook

### Step 6: Skills

Create three Claude Code skills:

1. **memory-create** - How to create memories
2. **memory-retrieve** - How to load and search memories
3. **memory-feedback** - How to provide feedback

Each skill includes:

- Function reference
- Code examples
- Best practices

### Step 7: CLI Tools

**ccmem** (binary):

- Core commands: search, list, show, reinforce, correct
- Compiled/binary implementation

**memory** (wrapper script):

- Extends ccmem with automation commands
- Handles: maintenance, automation status/load/unload

### Step 8: Automation Setup

**Launch Agent (macOS)**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.elche.memory-maintenance</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>/Users/elche/.claude/plugins/ccmem/scripts/maintenance.sh run</string>
    </array>
    <key>StartInterval</key>
    <integer>86400</integer>
</dict>
</plist>
```

## Key Implementation Details

### Memory File Format

```json
{
  "id": "2026-01-29T03-00-00-pnpm-preference",
  "version": "1.0.0",
  "type": "preference",
  "scope": {
    "type": "global",
    "path": null
  },
  "content": {
    "title": "Prefer pnpm over npm",
    "description": "User consistently uses pnpm",
    "action": "Suggest pnpm when discussing packages",
    "examples": ["pnpm install"]
  },
  "triggers": {
    "keywords": ["npm", "install"],
    "patterns": ["npm install"],
    "files": ["package.json"]
  },
  "metadata": {
    "confidence": 0.85,
    "created_at": "2026-01-29T03:00:00Z",
    "last_accessed": null,
    "access_count": 0,
    "positive_reinforcement": 0,
    "negative_reinforcement": 0,
    "source": "analyzer",
    "status": "active"
  },
  "evidence": [...],
  "tags": ["tooling", "javascript"],
  "relationships": {
    "related": [],
    "supersedes": null,
    "superseded_by": null
  }
}
```

### Confidence System

**Initial Confidence Calculation**:

```
confidence = (occurrences_weight * 0.4) +
             (consistency * 0.3) +
             (recency * 0.2) +
             (explicit_signal * 0.1)
```

**Adjustment Rules**:

- Accepted: +0.1
- Rejected: -0.2 (status → "under_review" if < 0.3)
- Superseded: status → "superseded"

**Decay Formula**:

```
decay_factor = 0.99 ^ days_since_access
adjusted = decay_factor * (0.5 + 0.5 * positive_ratio)
```

### Search Algorithm

Multi-factor scoring:

1. Keyword matches: +0.4 per field
2. Content match: +0.3
3. Tag overlap: +0.2 per tag
4. Pattern match: +0.5
5. Project boost: +0.3
6. Confidence weighting: final score × confidence

### Orphaned Session Recovery

When `on-start.sh` runs:

1. Find session IDs with `session_start` but no `session_end`
2. Exclude current active session
3. For each orphaned session:
   - Use last observation timestamp as end time
   - Calculate duration
   - Append synthetic `session_end` with `recovered: true`
   - Add to `sessions.json`

## Testing

### Unit Tests

Test individual components:

```bash
# Test memory creation
python3 -c "
import sys; sys.path.insert(0, 'scripts/lib')
from memory_lib import create_memory
mid = create_memory(...)
print(f'Created: {mid}')
"

# Test search
python3 -c "
import sys; sys.path.insert(0, 'scripts/lib')
from memory_lib import search_memories
results = search_memories('test')
print(f'Found: {len(results)}')
"
```

### Integration Tests

Test full workflow:

1. Start session (trigger on-start.sh)
2. Generate observations
3. Stop session (trigger on-stop.sh)
4. Run analyzer
5. Verify memories created
6. Search memories
7. Provide feedback

### Crash Recovery Test

1. Start Claude session
2. Generate some observations
3. Kill process (bypass on-stop.sh)
4. Start new session
5. Verify orphaned session is recovered

## Extending the System

### Adding New Memory Types

1. Add type to validation in `memory_lib.py`
2. Update skills documentation
3. Add example to CLAUDE.md

### Adding New Hooks

1. Create hook script in `hooks/`
2. Add to Claude Code settings.json
3. Document event format
4. Update analyzer to process new events

### Adding New Scripts

1. Create script in `scripts/`
2. Add to maintenance.sh if periodic
3. Add CLI command to `memory` wrapper
4. Document in README.md and CLAUDE.md

## Maintenance Tasks

### Daily (Automated)

- Process feedback
- Apply confidence decay
- Archive old observations
- Rebuild search index

### Weekly (Manual)

- Review low-confidence memories
- Check for duplicate memories
- Verify index integrity
- Review logs for errors

### Monthly (Manual)

- Archive very old observations
- Export memories for backup
- Review memory statistics
- Tune confidence thresholds

## Troubleshooting

### Common Issues

**Observation count mismatch**:

```bash
# Recalculate from observations file
wc -l ~/.claude/memory/observations.jsonl
```

**Corrupted index**:

```bash
# Rebuild from scratch
rm ~/.claude/memory/search-index.json
~/.claude/memory/scripts/build-index.py
```

**Orphaned sessions accumulating**:

```bash
# Check recovery logic
~/.claude/memory/hooks/on-start.sh
```

**Memory not found**:

```bash
# Check index consistency
jq '.memories.global[].id' ~/.claude/memory/index.json
ls ~/.claude/memory/memories/global/
```

## Security Considerations

- All data stays local in `~/.claude/memory/`
- No network access required
- No external APIs called
- Observations may contain sensitive data (file paths, commands)
- Consider git-ignoring `observations.jsonl` if in version control

## Performance Considerations

- Observations file grows unbounded (archive at 50k lines)
- Search index loaded into memory on query
- Memory files loaded on-demand
- Consider archiving memories with confidence < 0.1

## Documentation Updates

When modifying the memory system, update these files:

1. **CLAUDE.md** - Update agent guide with new APIs, behaviors
2. **BUILD.md** (this file) - Update build instructions, architecture
3. **README.md** - Update user-facing documentation
4. **Skill files** - Update Claude Code skill documentation

Keep all documentation in sync with the implementation.
