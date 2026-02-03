#!/bin/bash
# Memory System - Session Start Hook
# Initializes a new session and records the start event

set -e

MEMORY_DIR="${CLAUDE_MEMORY_DIR:-$HOME/.claude/memory}"
OBS_FILE="$MEMORY_DIR/observations.jsonl"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_FILE="$MEMORY_DIR/.current_session"
CONFIG_FILE="$MEMORY_DIR/config.json"
SESSIONS_FILE="$MEMORY_DIR/sessions.json"

# Ensure directory exists
mkdir -p "$(dirname "$OBS_FILE")"
mkdir -p "$MEMORY_DIR/logs"

# Recover orphaned sessions from previous crashed/killed sessions
recover_orphaned_sessions() {
    # Only proceed if observations file exists
    [ -f "$OBS_FILE" ] || return 0

    # Get current session ID if exists (don't recover the active session)
    local current_session_id=""
    if [ -f "$SESSION_FILE" ]; then
        current_session_id=$(cat "$SESSION_FILE" 2>/dev/null | tr -d '[:space:]')
    fi

    # Find all session IDs that have a start but no end
    local orphaned_sessions=()

    # Get all session IDs from session_start events
    local start_sessions
    start_sessions=$(jq -r 'select(.type == "session_start") | .session_id' "$OBS_FILE" 2>/dev/null | sort -u)

    # Get all session IDs from session_end events
    local end_sessions
    end_sessions=$(jq -r 'select(.type == "session_end") | .session_id' "$OBS_FILE" 2>/dev/null | sort -u)

    # Find orphaned sessions (in start but not in end, and not current session)
    while IFS= read -r session_id; do
        session_id=$(echo "$session_id" | tr -d '[:space:]')
        [ -n "$session_id" ] || continue
        # Skip if this is the current active session
        if [ "$session_id" = "$current_session_id" ]; then
            continue
        fi
        if ! echo "$end_sessions" | grep -qx "$session_id"; then
            orphaned_sessions+=("$session_id")
        fi
    done <<< "$start_sessions"

    # Skip if no orphaned sessions
    [ ${#orphaned_sessions[@]} -eq 0 ] && return 0

    # Log recovery attempt
    echo "MEMORY_SYSTEM: Recovering ${#orphaned_sessions[@]} orphaned session(s)" >&2

    local current_timestamp
    current_timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    for session_id in "${orphaned_sessions[@]}"; do
        # Get session start data (use -c for compact single-line output)
        local start_line
        start_line=$(jq -c "select(.session_id == \"$session_id\" and .type == \"session_start\")" "$OBS_FILE" 2>/dev/null | head -1)

        [ -n "$start_line" ] || continue

        local start_time
        start_time=$(echo "$start_line" | jq -r '.timestamp // empty' 2>/dev/null)

        local project_path
        project_path=$(echo "$start_line" | jq -r '.data.project_path // empty' 2>/dev/null)

        local project_hash
        project_hash=$(echo "$start_line" | jq -r '.data.project_hash // empty' 2>/dev/null)

        [ -n "$start_time" ] || continue

        # Count observations for this session
        local obs_count
        obs_count=$(jq -r "select(.session_id == \"$session_id\")" "$OBS_FILE" 2>/dev/null | wc -l | tr -d ' ')

        # Find last observation timestamp for this session (use as end time)
        local last_obs_time
        last_obs_time=$(jq -r "select(.session_id == \"$session_id\") | .timestamp" "$OBS_FILE" 2>/dev/null | tail -1)

        # Use last observation time, or current time if none found
        local end_time="${last_obs_time:-$current_timestamp}"

        # Calculate duration
        local duration_minutes=0
        local start_epoch
        start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$start_time" +%s 2>/dev/null || echo "0")
        local end_epoch
        end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$end_time" +%s 2>/dev/null || echo "0")

        if [ "$start_epoch" -gt 0 ] && [ "$end_epoch" -gt 0 ]; then
            duration_minutes=$(( (end_epoch - start_epoch) / 60 ))
        fi

        # Generate sequence number
        local sequence=1
        sequence=$(($(wc -l < "$OBS_FILE" 2>/dev/null || echo 0) + 1))

        # Append synthetic session_end event
        jq -nc \
            --arg ts "$end_time" \
            --arg sid "$session_id" \
            --argjson seq "$sequence" \
            --argjson duration "$duration_minutes" \
            --argjson count "$obs_count" \
            '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "session_end", data: {duration_minutes: $duration, observation_count: $count, recovered: true}}' \
            >> "$OBS_FILE" 2>/dev/null || continue

        # Update sessions.json
        if [ -n "$project_path" ]; then
            local tmp_file
            tmp_file=$(mktemp)

            if [ -f "$SESSIONS_FILE" ]; then
                jq --arg sid "$session_id" \
                   --arg path "$project_path" \
                   --arg hash "$project_hash" \
                   --arg start "$start_time" \
                   --arg end "$end_time" \
                   --argjson duration "$duration_minutes" \
                   --argjson count "$obs_count" \
                   '.sessions += [{id: $sid, project_path: $path, project_hash: $hash, started_at: $start, ended_at: $end, duration_minutes: $duration, observation_count: $count, recovered: true}] | .total_sessions = (.sessions | length)' \
                   "$SESSIONS_FILE" > "$tmp_file" 2>/dev/null && mv "$tmp_file" "$SESSIONS_FILE" || rm -f "$tmp_file"
            else
                jq -n \
                   --arg sid "$session_id" \
                   --arg path "$project_path" \
                   --arg hash "$project_hash" \
                   --arg start "$start_time" \
                   --arg end "$end_time" \
                   --argjson duration "$duration_minutes" \
                   --argjson count "$obs_count" \
                   '{sessions: [{id: $sid, project_path: $path, project_hash: $hash, started_at: $start, ended_at: $end, duration_minutes: $duration, observation_count: $count, recovered: true}], total_sessions: 1}' \
                   > "$SESSIONS_FILE" 2>/dev/null || true
            fi
        fi

        # Update config observation count
        if [ -f "$CONFIG_FILE" ]; then
            local tmp_config
            tmp_config=$(mktemp)
            jq --arg ts "$end_time" \
               --argjson count "$obs_count" \
               '.last_session = $ts | .identity.total_observations = ((.identity.total_observations // 0) + $count)' \
               "$CONFIG_FILE" > "$tmp_config" 2>/dev/null && mv "$tmp_config" "$CONFIG_FILE" || rm -f "$tmp_config"
        fi

        echo "MEMORY_SYSTEM: Recovered session $session_id (${duration_minutes}m, ${obs_count} observations)" >&2
    done

    # If .current_session references an orphaned session, clear it
    if [ -f "$SESSION_FILE" ]; then
        local current_sid
        current_sid=$(cat "$SESSION_FILE" 2>/dev/null)
        if [ -n "$current_sid" ]; then
            for sid in "${orphaned_sessions[@]}"; do
                if [ "$sid" = "$current_sid" ]; then
                    rm -f "$SESSION_FILE"
                    echo "MEMORY_SYSTEM: Cleared stale session marker" >&2
                    break
                fi
            done
        fi
    fi
}

# Recover any orphaned sessions before starting new one
recover_orphaned_sessions

# Generate new session ID
SESSION_ID=$(uuidgen 2>/dev/null || echo "session-$(date +%s)-$$")

# Store session ID for other hooks
echo "$SESSION_ID" > "$SESSION_FILE"

# Get project information (use git root if available)
CURRENT_PATH=$(pwd)

# Find git root for project path
find_git_root() {
    local dir="$1"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    echo "$1"
}

PROJECT_PATH=$(find_git_root "$CURRENT_PATH")
PROJECT_HASH=$(echo "$PROJECT_PATH" | shasum -a 256 2>/dev/null | cut -c1-8 || echo "unknown")

# Get timestamp
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Generate sequence number
SEQUENCE=1
if [ -f "$OBS_FILE" ]; then
    SEQUENCE=$(($(wc -l < "$OBS_FILE" 2>/dev/null || echo 0) + 1))
fi

# Write session start observation
jq -nc \
    --arg ts "$TIMESTAMP" \
    --arg sid "$SESSION_ID" \
    --argjson seq "$SEQUENCE" \
    --arg path "$PROJECT_PATH" \
    --arg hash "$PROJECT_HASH" \
    '{timestamp: $ts, session_id: $sid, sequence: $seq, type: "session_start", data: {project_path: $path, project_hash: $hash}}' \
    >> "$OBS_FILE" 2>/dev/null || true

# Update config with last_session timestamp
if [ -f "$CONFIG_FILE" ]; then
    TMP_FILE=$(mktemp)
    jq --arg ts "$TIMESTAMP" '.last_session = $ts' "$CONFIG_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$CONFIG_FILE" || rm -f "$TMP_FILE"
fi

# Signal that we're ready (for potential background analyzer)
if [ -f "$OBS_FILE" ]; then
    OBS_COUNT=$(wc -l < "$OBS_FILE" 2>/dev/null || echo 0)
    if [ "$OBS_COUNT" -gt 1000 ]; then
        echo "MEMORY_SYSTEM: Analysis recommended ($OBS_COUNT observations)" >&2
    fi
fi

# Check for promotion candidates (notification only - no auto-promote)
if [ -f "$PLUGIN_DIR/hooks/promote-candidates.sh" ]; then
    bash "$PLUGIN_DIR/hooks/promote-candidates.sh" 2>/dev/null || true
fi

exit 0
