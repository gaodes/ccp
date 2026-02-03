#!/bin/bash
# ccmem - Promotion Candidate Notification Hook
# Checks if memories are candidates for CLAUDE.md promotion and notifies user
# Does NOT auto-promote - user must run 'ccmem promote' manually

set -e

MEMORY_DIR="${CLAUDE_MEMORY_DIR:-$HOME/.claude/memory}"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Only check, don't promote
if [ -f "$PLUGIN_DIR/scripts/promote-workflow.py" ]; then
    count=$(python3 "$PLUGIN_DIR/scripts/promote-workflow.py" --check-only 2>/dev/null | grep -o '[0-9]\+' | head -1 || echo "0")

    if [ "$count" -gt 0 ] 2>/dev/null; then
        echo "ccmem: $count memories ready for CLAUDE.md review. Run 'ccmem promote' to review and approve them." >&2
    fi
fi

exit 0
