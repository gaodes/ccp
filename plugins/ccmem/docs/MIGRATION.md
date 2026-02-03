# Memory System Migration to Plugin Architecture

---

## Version: 1.0.1 → 1.0.2

## Migration Date

2026-02-02

## Migration Type

Patch release - CLI command standardization.

## What Changed

### CLI Command Standardization
- All documentation updated to use `ccmem` as the primary command
- The `memory` wrapper script remains for backward compatibility
- Examples and help text now consistently use `ccmem`

### Documentation Updates
- **README.md**: All command examples changed from `memory` to `ccmem`
- **BUILD.md**: Updated plist example paths to use plugin directory

## Compatibility

- **Backward Compatible**: The `memory` command wrapper still works
- **Recommended**: Use `ccmem` for all new scripts and documentation
- **CLI Commands**: Both `ccmem` and `memory` continue to work

## Verification

```bash
# Test primary CLI
ccmem stats

# Test legacy wrapper (should still work)
memory stats

# Both should produce the same output
```

---

## Version: 1.0.0 → 1.0.1

## Migration Date

2026-02-02 03:37 UTC

## Migration Type

Patch release - Plugin architecture reorganization with backward-compatible changes.

## What Changed

### Moved to Plugin Directory (`~/.claude/plugins/ccmem/`)
- `hooks/` → `plugins/ccmem/hooks/`
- `scripts/` → `plugins/ccmem/scripts/`
- `skills/` → `plugins/ccmem/skills/`
- `agents/` → `plugins/ccmem/agents/`
- `bin/` → `plugins/ccmem/bin/`
- `automation/` → `plugins/ccmem/automation/`
- `*.md` (docs) → `plugins/ccmem/docs/`

### Remained in Memory Directory (`~/.claude/memory/`)
- `config.json` - System configuration
- `index.json` - Master memory index
- `observations.jsonl` - Event stream
- `feedback.jsonl` - User feedback log
- `search-index.json` - Search index
- `sessions.json` - Session history
- `.current_session` - Current session marker
- `memories/` - Memory storage (global/ and projects/)
- `logs/` - Maintenance logs
- `exports/` - Memory exports
- `.claude/` - Internal data

## Path Changes

### Updated Files

| File | Old Path | New Path |
|------|----------|----------|
| `memory_lib.py` | `~/.claude/memory/scripts/lib/` | `~/.claude/plugins/ccmem/scripts/lib/` |
| `bin/ccmem` | `~/.claude/memory/bin/` | `~/.claude/plugins/ccmem/bin/` |
| `bin/memory` | `~/.claude/memory/bin/` | `~/.claude/plugins/ccmem/bin/` |
| `hooks/on-start.sh` | `~/.claude/memory/hooks/` | `~/.claude/plugins/ccmem/hooks/` |
| `hooks/capture.sh` | `~/.claude/memory/hooks/` | `~/.claude/plugins/ccmem/hooks/` |
| `hooks/on-stop.sh` | `~/.claude/memory/hooks/` | `~/.claude/plugins/ccmem/hooks/` |
| `scripts/maintenance.sh` | `~/.claude/memory/scripts/` | `~/.claude/plugins/ccmem/scripts/` |
| `automation/*.plist` | `~/.claude/memory/` | `~/.claude/plugins/ccmem/automation/` |
| `docs/*.md` | `~/.claude/memory/` | `~/.claude/plugins/ccmem/docs/` |

### Settings.json Changes

Updated hook paths in `~/.claude/settings.json`:
- `$HOME/.claude/memory/hooks/` → `$HOME/.claude/plugins/ccmem/hooks/`

## Environment Variables

The system now supports:

- `CLAUDE_MEMORY_DIR`: Runtime data location (default: `~/.claude/memory`)
- `CLAUDE_PLUGIN_DIR`: Plugin codebase location (default: `~/.claude/plugins/ccmem`)

## Rollback Instructions

If needed, rollback is possible:

1. **Stop automation**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.elche.memory-maintenance.plist
   ```

2. **Restore from backup**
   ```bash
   # Find backup directory
   ls -la ~/.claude/memory-backup-*

   # Restore (replace TIMESTAMP with actual backup)
   rm -rf ~/.claude/memory
   cp -r ~/.claude/memory-backup-TIMESTAMP ~/.claude/memory
   ```

3. **Restore old settings.json hooks**
   ```bash
   # Edit ~/.claude/settings.json
   # Change: $HOME/.claude/plugins/ccmem/hooks/
   # Back to: $HOME/.claude/memory/hooks/
   ```

4. **Move code back** (if backup not available)
   ```bash
   mv ~/.claude/plugins/ccmem/* ~/.claude/memory/
   rmdir ~/.claude/plugins/ccmem
   ```

5. **Reload automation** (if needed)
   ```bash
   launchctl load ~/Library/LaunchAgents/com.elche.memory-maintenance.plist
   ```

6. **Restart Claude Code**

## Benefits of New Structure

1. **Clear Separation**: Code and data are now in separate locations
2. **Easier Updates**: The plugin can be updated without touching data
3. **Better Organization**: Follows standard plugin architecture patterns
4. **Future Flexibility**: Runtime data can be customized via environment variables
5. **Backup Simplicity**: Can backup just data or just code independently

## Compatibility

- **Claude Code**: Requires restart to load new hook paths
- **CLI Commands**: Continue to work from PATH
- **Automation**: Launch agent updated with new paths
- **Skills**: All skills updated with new import paths

## Verification

To verify the migration was successful:

```bash
# Check plugin structure
ls -la ~/.claude/plugins/ccmem/

# Check runtime data
ls -la ~/.claude/memory/

# Test CLI
~/.claude/plugins/ccmem/bin/ccmem stats

# Verify hooks work
# (Hooks will be tested on next Claude Code session)
```
