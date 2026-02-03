# CLAUDE.md — ccmem Plugin Development

## Project Identity

**ccmem** is a Claude Code plugin that implements a file-based memory system. When working here, you are modifying the plugin itself, not using the memory system.

## Development Workflow

### Making Changes

1. Edit plugin files in this repository
2. Uninstall/reinstall the plugin to pick up changes:
   ```
   /plugin uninstall ccmem@ccmem-dev
   /plugin install ccmem@ccmem-dev
   ```
3. Restart Claude Code to reload hooks and skills

### Testing

- Use `./bin/ccmem` directly for CLI testing: `./bin/ccmem stats`
- Check hooks fire: observe `~/.claude/memory/observations.jsonl`
- Verify skill loads: `/ccmem-stats` should invoke the skill

### Release Process

1. Update version in `.claude-plugin/plugin.json`
2. Update version in `.claude-plugin/marketplace.json`
3. Commit changes with conventional commit message
4. Test with clean install in another session

## Codebase Structure

```
ccmem/
├── .claude-plugin/          # Plugin manifests (version, hooks, skills)
├── hooks/                   # Claude Code event capture scripts
├── scripts/lib/             # Core Python library (memory_lib.py)
├── skills/                  # Claude Code skills (SKILL.md files)
├── agents/                  # Analyzer agent instructions
├── bin/                     # CLI entry points (ccmem, memory)
├── commands/                # Slash command documentation
├── automation/              # macOS launch agent plist
├── docs/                    # Additional documentation
├── README.md                # User-facing documentation
├── BUILD.md                 # Build/architecture guide
└── CLAUDE.md                # This file
```

## Key Files When Modifying

| Change Target | Files to Edit | Also Update |
|---------------|---------------|-------------|
| Add new hook | `hooks/<name>.sh` | `.claude-plugin/plugin.json` |
| Add new skill | `skills/<name>/SKILL.md` | `.claude-plugin/plugin.json` |
| Add new CLI command | `bin/ccmem` | `commands/<name>.md` |
| Change memory schema | `scripts/lib/memory_lib.py` | `BUILD.md` |
| Change plugin version | `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` |

## Runtime Data Location

The plugin operates on `~/.claude/memory/` (configurable via `CLAUDE_MEMORY_DIR`). This is **separate** from this source repository.

## Design Principles

- **Zero dependencies** - Only bash, python3, jq
- **File-based** - Everything is JSON/JSONL text files
- **Append-only** - Observations never mutated, only archived
- **Atomic updates** - Use temp files + move for index/config writes

## Testing Changes Locally

```bash
# Test CLI directly
./bin/ccmem stats
./bin/ccmem list
./bin/ccmem search "test"

# Test hook (capture will write to ~/.claude/memory/observations.jsonl)
./hooks/capture.sh prompt "test prompt" "test description"

# Verify memory operations
python3 -c "
import sys
sys.path.insert(0, 'scripts/lib')
from memory_lib import list_memories
print(f'Memories: {len(list_memories())}')
"
```

## Common Tasks

### Add a new CLI command

1. Add function to `bin/ccmem`
2. Add case to `main()` dispatcher
3. Update help text in `show_help()`
4. Document in `commands/<command>.md`

### Add a new skill

1. Create `skills/<skill-name>/SKILL.md`
2. Register in `.claude-plugin/plugin.json` under `skills`
3. Test with `/ccmem:<skill-name>`

### Modify memory schema

1. Edit `scripts/lib/memory_lib.py`
2. Update `BUILD.md` with new format
3. Rebuild search index: `./scripts/lib/build-index.py`

## Debugging

**Hook not firing?** Check `.claude-plugin/plugin.json` syntax and reload plugin.

**Memory not found?** Check `~/.claude/memory/index.json` vs actual files in `memories/`.

**Search broken?** Rebuild index: `./scripts/build-index.py` (from memory dir).

## Documentation Hierarchy

1. **CLAUDE.md** (this) - For agents working on the plugin codebase
2. **BUILD.md** - Architecture, build instructions, implementation details
3. **README.md** - User-facing installation and usage
4. **Skill files** - Runtime guidance for memory operations

When updating functionality, update the relevant documentation files above.
