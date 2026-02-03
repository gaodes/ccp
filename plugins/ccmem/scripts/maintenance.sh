#!/bin/bash
#
# Memory System Maintenance Script
#
# Performs periodic maintenance on the memory system:
# - Process pending feedback
# - Apply confidence decay
# - Archive old observations
# - Rebuild search index if needed
# - Update configuration
#

set -e

# Configuration
MEMORY_DIR="${CLAUDE_MEMORY_DIR:-$HOME/.claude/memory}"
CONFIG_FILE="${MEMORY_DIR}/config.json"
OBSERVATIONS_FILE="${MEMORY_DIR}/observations.jsonl"
ARCHIVE_FILE="${MEMORY_DIR}/observations.archive.jsonl"
SCRIPTS_DIR="${CLAUDE_PLUGIN_DIR:-$HOME/.claude/plugins/ccmem}/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if memory directory exists
check_memory_dir() {
    if [[ ! -d "${MEMORY_DIR}" ]]; then
        log_error "Memory directory not found: ${MEMORY_DIR}"
        exit 1
    fi
}

# Update last maintenance timestamp in config
update_config() {
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Use Python to update JSON
    python3 << EOF
import json
import sys

try:
    with open('${CONFIG_FILE}', 'r') as f:
        config = json.load(f)

    config['last_maintenance'] = '${timestamp}'

    with open('${CONFIG_FILE}', 'w') as f:
        json.dump(config, f, indent=2)

    print("Updated last_maintenance timestamp")
except Exception as e:
    print(f"Error updating config: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Archive old observations (move processed observations to archive)
archive_observations() {
    log_info "Archiving observations..."

    if [[ ! -f "${OBSERVATIONS_FILE}" ]]; then
        log_warning "No observations file found"
        return 0
    fi

    local line_count
    line_count=$(wc -l < "${OBSERVATIONS_FILE}" 2>/dev/null || echo 0)
    line_count=$(echo "$line_count" | tr -d ' ')

    # Get archive threshold from config
    local archive_threshold
    archive_threshold=$(python3 -c "
import json
with open('${CONFIG_FILE}') as f:
    config = json.load(f)
print(config.get('settings', {}).get('archive_threshold', 50000))
" 2>/dev/null || echo 50000)

    if [[ "$line_count" -gt "$archive_threshold" ]]; then
        log_info "Observations ($line_count) exceed threshold ($archive_threshold), archiving..."

        # Create archive file if it doesn't exist
        touch "${ARCHIVE_FILE}"

        # Move older observations to archive (keep last 10000)
        local keep_count=10000
        local archive_count=$((line_count - keep_count))

        if [[ "$archive_count" -gt 0 ]]; then
            head -n "$archive_count" "${OBSERVATIONS_FILE}" >> "${ARCHIVE_FILE}"
            tail -n "$keep_count" "${OBSERVATIONS_FILE}" > "${OBSERVATIONS_FILE}.tmp"
            mv "${OBSERVATIONS_FILE}.tmp" "${OBSERVATIONS_FILE}"
            log_success "Archived $archive_count observations"
        fi
    else
        log_info "Observations within threshold ($line_count / $archive_threshold)"
    fi
}

# Process feedback and update confidence
process_feedback() {
    log_info "Processing pending feedback..."

    if [[ -f "${SCRIPTS_DIR}/update-confidence.py" ]]; then
        python3 "${SCRIPTS_DIR}/update-confidence.py" --feedback
    else
        log_warning "update-confidence.py not found, skipping feedback processing"
    fi
}

# Apply confidence decay
apply_decay() {
    log_info "Applying confidence decay..."

    if [[ -f "${SCRIPTS_DIR}/update-confidence.py" ]]; then
        python3 "${SCRIPTS_DIR}/update-confidence.py" --decay
    else
        log_warning "update-confidence.py not found, skipping decay"
    fi
}

# Rebuild search index if needed
rebuild_index() {
    log_info "Checking search index..."

    local search_index="${MEMORY_DIR}/search-index.json"
    local needs_rebuild=false

    # Check if index exists and is recent (within 24 hours)
    if [[ ! -f "$search_index" ]]; then
        log_info "Search index not found, needs rebuild"
        needs_rebuild=true
    elif [[ -n "$(find "$search_index" -mtime +1 2>/dev/null)" ]]; then
        log_info "Search index is older than 24 hours, needs rebuild"
        needs_rebuild=true
    fi

    if [[ "$needs_rebuild" == true ]] && [[ -f "${SCRIPTS_DIR}/build-index.py" ]]; then
        log_info "Rebuilding search index..."
        python3 "${SCRIPTS_DIR}/build-index.py"
        log_success "Search index rebuilt"
    else
        log_info "Search index is up to date"
    fi
}

# Show current statistics
show_stats() {
    log_info "Memory System Statistics"
    echo "=========================="

    # Config stats
    if [[ -f "$CONFIG_FILE" ]]; then
        python3 << EOF
import json

try:
    with open('${CONFIG_FILE}') as f:
        config = json.load(f)

    identity = config.get('identity', {})
    settings = config.get('settings', {})

    print(f"Version:          {config.get('version', 'unknown')}")
    print(f"Created:          {config.get('created_at', 'unknown')}")
    print(f"Sessions:         {identity.get('session_count', 0)}")
    print(f"Observations:     {identity.get('total_observations', 0)}")
    print(f"Total Memories:   {identity.get('total_memories', 0)}")
    print(f"Last Session:     {config.get('last_session', 'never')}")
    print(f"Last Maintenance: {config.get('last_maintenance', 'never')}")
except Exception as e:
    print(f"Error reading config: {e}")
EOF
    fi

    echo ""

    # File stats
    if [[ -f "$OBSERVATIONS_FILE" ]]; then
        local obs_count
        obs_count=$(wc -l < "$OBSERVATIONS_FILE" | tr -d ' ')
        echo "Observations file: $obs_count lines"
    fi

    if [[ -f "$ARCHIVE_FILE" ]]; then
        local archive_count
        archive_count=$(wc -l < "$ARCHIVE_FILE" | tr -d ' ')
        echo "Archive file:      $archive_count lines"
    fi

    # Memory counts
    local global_count=0
    local project_count=0

    if [[ -d "${MEMORY_DIR}/memories/global" ]]; then
        global_count=$(find "${MEMORY_DIR}/memories/global" -name "*.json" | wc -l | tr -d ' ')
    fi

    if [[ -d "${MEMORY_DIR}/memories/projects" ]]; then
        project_count=$(find "${MEMORY_DIR}/memories/projects" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
    fi

    echo "Global memories:   $global_count"
    echo "Project memories:  $project_count"
}

# Full maintenance run
run_maintenance() {
    log_info "Starting memory system maintenance..."
    echo ""

    check_memory_dir

    process_feedback
    echo ""

    apply_decay
    echo ""

    archive_observations
    echo ""

    rebuild_index
    echo ""

    update_config

    echo ""
    log_success "Maintenance complete!"
    echo ""

    show_stats
}

# Show help
show_help() {
    cat << EOF
Memory System Maintenance

Usage: maintenance.sh [COMMAND]

Commands:
  run         Run full maintenance (default)
  stats       Show current statistics
  feedback    Process pending feedback only
  decay       Apply confidence decay only
  archive     Archive old observations only
  index       Rebuild search index only
  help        Show this help message

Examples:
  maintenance.sh              # Run full maintenance
  maintenance.sh stats        # Show statistics
  maintenance.sh feedback     # Process feedback only
EOF
}

# Main entry point
main() {
    local command="${1:-run}"

    case "$command" in
        run)
            run_maintenance
            ;;
        stats)
            check_memory_dir
            show_stats
            ;;
        feedback)
            check_memory_dir
            process_feedback
            ;;
        decay)
            check_memory_dir
            apply_decay
            ;;
        archive)
            check_memory_dir
            archive_observations
            ;;
        index)
            check_memory_dir
            rebuild_index
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
