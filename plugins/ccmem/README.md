# ccmem - Claude Code Memory System

A file-based memory system for Claude Code that learns from observations and improves over time.

## Installation

### As Claude Code Plugin (Recommended)

```bash
# Add the plugin marketplace
/plugin marketplace add /path/to/ccmem

# Install the plugin
/plugin install ccmem@ccmem-dev

# Restart Claude Code to activate
```

### Manual Installation

```bash
# Clone or copy to ~/.claude/memory/
# Set up hooks in Claude Code settings
```

### CLI Setup (Optional)

To use the `ccmem` CLI directly from your terminal, add the plugin's bin directory to your PATH:

```bash
# Find where the plugin is installed
CCMEM_PATH=$(find ~/.claude/plugins -name "ccmem" -type f -path "*/bin/*" 2>/dev/null | head -1 | xargs dirname)

# Add to your shell profile (~/.zshrc or ~/.bashrc)
export PATH="$CCMEM_PATH:$PATH"
```

Alternatively, use slash commands in Claude Code (no PATH setup needed):
- `/ccmem-stats` — View statistics
- `/ccmem-list` — List memories
- `/ccmem-search <query>` — Search memories
- `/ccmem-show <id>` — Show memory details
- `/ccmem-remember <description>` — Create a memory
- `/ccmem-reinforce <id>` — Positive feedback
- `/ccmem-correct <id>` — Negative feedback
- `/ccmem-promote` — Review and promote to CLAUDE.md
- `/ccmem-cleanup` — Review low-confidence memories

## Quick Start

```bash
# View statistics
ccmem stats

# Search memories
ccmem search "pnpm"
ccmem search "workflow"

# List all memories
ccmem list

# Show specific memory
ccmem show <memory-id>

# Provide feedback
ccmem reinforce <memory-id>    # Positive feedback
ccmem correct <memory-id>      # Negative feedback

# Run maintenance manually
ccmem maintenance

# Check automation status
ccmem automation status

# Unload automation
ccmem automation unload
```

## Orphaned Session Recovery

If Claude Code crashes or is killed abruptly (terminal closed, process killed), sessions may be left without a proper `session_end` event. The system automatically detects and recovers these orphaned sessions:

- Recovery happens at the start of each new session
- Orphaned sessions are finalized with synthetic `session_end` events
- Marked with `"recovered": true` in `sessions.json`
- Current active session is never recovered

## Configuration

Set `CLAUDE_MEMORY_DIR` environment variable to customize where memory data is stored:

```bash
export CLAUDE_MEMORY_DIR="/custom/path/to/memory"
```

Default: `~/.claude/memory/`

## Directory Structure

```
~/.claude/memory/
├── config.json              # System configuration
├── index.json               # Master memory index
├── observations.jsonl       # Event stream (hooks write here)
├── feedback.jsonl           # User feedback log
├── search-index.json        # Full-text search index
├── memories/
│   ├── global/              # Global memories
│   └── projects/            # Per-project memories
├── hooks/                   # Claude Code hooks
├── scripts/                 # Utility scripts
├── skills/                  # Claude Code skills
└── bin/                     # CLI commands
```

## How It Works

1. **Capture**: Hooks capture session events (prompts, tool uses) to `observations.jsonl`
2. **Analyze**: The analyzer detects patterns and creates memory files
3. **Retrieve**: The system searches relevant memories based on context
4. **Learn**: Feedback adjusts confidence; unused memories decay over time
5. **Sync**: High-confidence memories (≥0.8) automatically sync to CLAUDE.md

## CLAUDE.md Integration

High-confidence memories (≥0.8) are automatically synced to your CLAUDE.md file at session start:

```markdown
<!-- memory-sync: start -->
<!-- These sections are auto-updated from high-confidence memories -->

### Active Memories (High Confidence)
- prefer-pnpm-over-npm (0.85) — Suggest pnpm for Node.js projects
- prefer-task-based-workflow (0.90) — Use TodoWrite for complex tasks
...

<!-- memory-sync: end -->
```

**How it works:**
- The `on-start.sh` hook automatically runs `ccmem sync --promote`
- Memories with confidence ≥0.8 are formatted and inserted between sync markers
- Manual sections outside sync markers are preserved
- Memories can be reinforced (`ccmem reinforce`) or corrected (`ccmem correct`)

**Manual sync:**
```bash
# Promote high-confidence memories to CLAUDE.md
ccmem sync --promote

# Import CLAUDE.md rules back to memories
ccmem sync --import

# Two-way sync
ccmem sync
```

## Automation

### Option 1: Launch Agent (macOS)

```bash
# Install the launch agent
cp ~/.claude/memory/com.elche.memory-maintenance.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.elche.memory-maintenance.plist

# Verify it's loaded
launchctl list | grep memory-maintenance
```

Runs daily at midnight.

### Option 2: Cron (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add line for daily maintenance at 2 AM
0 2 * * * ~/.claude/memory/scripts/maintenance.sh run
```

### Option 3: Manual

Run maintenance whenever convenient:
```bash
ccmem maintenance
```

## CLI Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `ccmem search <query>` | Search memories by content |
| `ccmem list` | List all memories |
| `ccmem show <id>` | Show memory details |
| `ccmem reinforce <id>` | Positive feedback (increases confidence) |
| `ccmem correct <id>` | Negative feedback (decreases confidence) |
| `ccmem stats` | Show system statistics |

### Analysis Commands

| Command | Description |
|---------|-------------|
| `ccmem analyze` | Run pattern analysis on observations |
| `ccmem index` | Rebuild search index |
| `ccmem sync` | Sync with CLAUDE.md |

### Automation Commands

| Command | Description |
|---------|-------------|
| `ccmem maintenance` | Run maintenance manually |
| `ccmem automation status` | Check automation status |
| `ccmem automation load` | Load launch agent |
| `ccmem automation unload` | Unload launch agent |

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| preference | User likes/dislikes | "Prefer pnpm over npm" |
| pattern | Code/workflow patterns | "Use early returns" |
| correction | Learned from mistakes | "User prefers Zod" |
| workflow | Preferred processes | "Run tests first" |
| negative | What NOT to do | "Never suggest MD5" |

## Confidence System

- **Initial**: Based on pattern strength (0.5 - 0.95)
- **Reinforcement**: +0.1 for positive feedback
- **Correction**: -0.2 for negative feedback
- **Decay**: Loses ~1% per day of inactivity
- **Archive**: Memories below 0.1 confidence are archived

## Skills

Use these Claude Code skills for memory operations:

- `memory-create` - Create new memories
- `memory-retrieve` - Load and apply memories
- `memory-feedback` - Provide feedback on memories

## Files

| File | Purpose |
|------|---------|
| `config.json` | System identity, settings, timestamps |
| `index.json` | Master index of all memories |
| `observations.jsonl` | Append-only event stream |
| `feedback.jsonl` | User feedback and corrections |
| `search-index.json` | Inverted index for search |

## Current Status

Run `ccmem stats` to see:
- Total observations captured
- Number of memories
- Last analysis timestamp
- Last maintenance timestamp

## Troubleshooting

**No memories found?**
- Check if analyzer has run: `cat config.json | grep last_analysis`
- Run manually: `python3 ~/.claude/memory/scripts/lib/memory_lib.py`

**Search not working?**
- Rebuild index: `~/.claude/memory/scripts/build-index.py`

**Maintenance failing?**
- Check logs: `cat ~/.claude/memory/logs/maintenance-error.log`

## Privacy

100% local. All data stays in `~/.claude/memory/`. No external services.
