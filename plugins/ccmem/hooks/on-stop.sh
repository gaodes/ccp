#!/bin/bash
# Memory System - Session Stop Hook
# Finalizes the session and records the end event

set -e

MEMORY_DIR="${CLAUDE_MEMORY_DIR:-$HOME/.claude/memory}"
OBS_FILE="$MEMORY_DIR/observations.jsonl"
SESSION_FILE="$MEMORY_DIR/.current_session"
CONFIG_FILE="$MEMORY_DIR/config.json"
SESSIONS_FILE="$MEMORY_DIR/sessions.json"

# Get session ID
SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null || echo "unknown")

# Get timestamp
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Generate sequence number
SEQUENCE=1
if [ -f "$OBS_FILE" ]; then
    SEQUENCE=$(($(wc -l < "$OBS_FILE" 2>/dev/null || echo 0) + 1))
fi

# Calculate session stats
OBSERVATION_COUNT=0
START_TIME=""
PROJECT_PATH=""
PROJECT_HASH=""

if [ -f "$OBS_FILE" ]; then
    # Count observations for this session
    OBSERVATION_COUNT=$(grep "\"session_id\":\"$SESSION_ID\"" "$OBS_FILE" 2>/dev/null | wc -l | tr -d ' ')

    # Find session start time
    START_LINE=$(grep "\"session_id\":\"$SESSION_ID\"" "$OBS_FILE" 2>/dev/null | grep "\"type\":\"session_start\"" | head -1)
    START_TIME=$(echo "$START_LINE" | jq -r '.timestamp // empty' 2>/dev/null || echo "")
    PROJECT_PATH=$(echo "$START_LINE" | jq -r '.data.project_path // empty' 2>/dev/null || echo "")
    PROJECT_HASH=$(echo "$START_LINE" | jq -r '.data.project_hash // empty' 2>/dev/null || echo "")
fi

# Calculate duration
DURATION_MINUTES=0
if [ -n "$START_TIME" ]; then
    START_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" +%s 2>/dev/null || echo "0")
    END_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$TIMESTAMP" +%s 2>/dev/null || echo "0")
    if [ "$START_EPOCH" -gt 0 ] && [ "$END_EPOCH" -gt 0 ]; then
        DURATION_MINUTES=$(( (END_EPOCH - START_EPOCH) / 60 ))
    fi
fi

# Write session end observation
jq -nc \
    --arg ts "$TIMESTAMP" \
    --arg sid "$SESSION_ID" \
    --argjson seq "$SEQUENCE" \
    --argjson duration "$DURATION_MINUTES" \
    --argjson count "$OBSERVATION_COUNT" \
    '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "session_end", data: {duration_minutes: $duration, observation_count: $count}}' \
    >> "$OBS_FILE" 2>/dev/null || true

# Update sessions index
if [ -n "$PROJECT_PATH" ] && [ -n "$START_TIME" ]; then
    TMP_FILE=$(mktemp)
    if [ -f "$SESSIONS_FILE" ]; then
        # Add to existing sessions
        jq --arg sid "$SESSION_ID" \
           --arg path "$PROJECT_PATH" \
           --arg hash "$PROJECT_HASH" \
           --arg start "$START_TIME" \
           --arg end "$TIMESTAMP" \
           --argjson duration "$DURATION_MINUTES" \
           --argjson count "$OBSERVATION_COUNT" \
           '.sessions += [{id: $sid, project_path: $path, project_hash: $hash, started_at: $start, ended_at: $end, duration_minutes: $duration, observation_count: $count}] | .total_sessions = (.sessions | length)' \
           "$SESSIONS_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$SESSIONS_FILE" || rm -f "$TMP_FILE"
    else
        # Create new sessions file
        jq -n \
           --arg sid "$SESSION_ID" \
           --arg path "$PROJECT_PATH" \
           --arg hash "$PROJECT_HASH" \
           --arg start "$START_TIME" \
           --arg end "$TIMESTAMP" \
           --argjson duration "$DURATION_MINUTES" \
           --argjson count "$OBSERVATION_COUNT" \
           '{sessions: [{id: $sid, project_path: $path, project_hash: $hash, started_at: $start, ended_at: $end, duration_minutes: $duration, observation_count: $count}], total_sessions: 1}' \
           > "$SESSIONS_FILE" 2>/dev/null || true
    fi
fi

# Update config
if [ -f "$CONFIG_FILE" ]; then
    TMP_FILE=$(mktemp)
    jq --arg ts "$TIMESTAMP" \
       --argjson count "$OBSERVATION_COUNT" \
       '.last_session = $ts | .identity.total_observations = ((.identity.total_observations // 0) + $count)' \
       "$CONFIG_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$CONFIG_FILE" || rm -f "$TMP_FILE"
fi

# Clean up session file
rm -f "$SESSION_FILE"

exit 0
