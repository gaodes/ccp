#!/bin/bash
# Memory System - Event Capture Hook
# Captures prompts and tool usage to observations.jsonl
# Append-only, non-blocking. Never fails (exit 0 always).

set -e

EVENT_TYPE="${1:-unknown}"
MEMORY_DIR="${CLAUDE_MEMORY_DIR:-$HOME/.claude/memory}"
OBS_FILE="$MEMORY_DIR/observations.jsonl"
SESSION_FILE="$MEMORY_DIR/.current_session"

# Ensure directory exists
mkdir -p "$(dirname "$OBS_FILE")"

# Get session ID (create if doesn't exist)
if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE")
else
    SESSION_ID=$(uuidgen 2>/dev/null || echo "session-$(date +%s)")
    echo "$SESSION_ID" > "$SESSION_FILE"
fi

# Get timestamp
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Generate sequence number (line count + 1)
SEQUENCE=1
if [ -f "$OBS_FILE" ]; then
    SEQUENCE=$(($(wc -l < "$OBS_FILE" 2>/dev/null || echo 0) + 1))
fi

# Build observation JSON based on event type
case "$EVENT_TYPE" in
  prompt)
    # Read prompt from stdin (hook data as JSON)
    INPUT=$(cat)
    PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null || echo "")
    if [ -n "$PROMPT" ]; then
      # Truncate long prompts to save space (max 500 chars)
      PROMPT_SHORT=$(echo "$PROMPT" | cut -c1-500)
      # Escape for JSON
      PROMPT_ESCAPED=$(echo "$PROMPT_SHORT" | jq -Rs '.[:-1]')
      jq -nc \
        --arg ts "$TIMESTAMP" \
        --arg sid "$SESSION_ID" \
        --argjson seq "$SEQUENCE" \
        --argjson prompt "$PROMPT_ESCAPED" \
        '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "prompt", data: {prompt: $prompt, length: ($prompt | length)}}' >> "$OBS_FILE" 2>/dev/null || true
    fi
    ;;

  tool)
    # Read tool data from stdin
    INPUT=$(cat)
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")

    if [ -n "$TOOL_NAME" ]; then
      # Extract tool input (safely)
      TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")

      # For Bash tool, extract command for easier reading
      COMMAND_DESC=""
      if [ "$TOOL_NAME" = "Bash" ]; then
        COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")
        if [ -n "$COMMAND" ]; then
          # Truncate long commands
          COMMAND_DESC=$(echo "$COMMAND" | cut -c1-200)
        fi
      fi

      jq -nc \
        --arg ts "$TIMESTAMP" \
        --arg sid "$SESSION_ID" \
        --argjson seq "$SEQUENCE" \
        --arg tool "$TOOL_NAME" \
        --argjson input "$TOOL_INPUT" \
        --arg desc "$COMMAND_DESC" \
        '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "tool_use", data: {tool: $tool, input: $input, description: $desc}}' >> "$OBS_FILE" 2>/dev/null || true
    fi
    ;;

  file)
    # File modification events
    INPUT=$(cat)
    FILE_PATH=$(echo "$INPUT" | jq -r '.path // empty' 2>/dev/null || echo "")
    if [ -n "$FILE_PATH" ]; then
      CHANGE_TYPE=$(echo "$INPUT" | jq -r '.change_type // "modified"' 2>/dev/null || echo "modified")
      jq -nc \
        --arg ts "$TIMESTAMP" \
        --arg sid "$SESSION_ID" \
        --argjson seq "$SEQUENCE" \
        --arg path "$FILE_PATH" \
        --arg change "$CHANGE_TYPE" \
        '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "file_modified", data: {path: $path, change_type: $change}}' >> "$OBS_FILE" 2>/dev/null || true
    fi
    ;;

  *)
    # Unknown event type - log minimal info
    INPUT=$(cat)
    jq -nc \
      --arg ts "$TIMESTAMP" \
      --arg sid "$SESSION_ID" \
      --argjson seq "$SEQUENCE" \
      --arg type "$EVENT_TYPE" \
      --arg raw "$INPUT" \
      '{timestamp: $ts, session_id: $sid, sequence: $seq, type: $type, data: {raw: $raw}}' >> "$OBS_FILE" 2>/dev/null || true
    ;;
esac

# Always exit 0 - never block the session
exit 0
