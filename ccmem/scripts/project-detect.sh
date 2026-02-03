#!/bin/bash
#
# Project Detection Script
# Detects the current project root and generates project hash.
#
# Usage:
#   project-detect.sh [path]
#   project-detect.sh --hash-only [path]
#   project-detect.sh --info [path]
#
# Output:
#   Default: project_hash
#   --hash-only: hash only
#   --info: JSON with path, hash, git_root, and name
#

set -e

# Get the directory to analyze (default: current directory)
TARGET_PATH="${1:-$(pwd)}"

# Check for flags
FLAG=""
if [[ "$TARGET_PATH" == --* ]]; then
    FLAG="$TARGET_PATH"
    TARGET_PATH="${2:-$(pwd)}"
fi

# Resolve to absolute path
if [[ "$TARGET_PATH" == /* ]]; then
    ABS_PATH="$TARGET_PATH"
else
    ABS_PATH="$(cd "$TARGET_PATH" && pwd)"
fi

# Find git root (if in a git repository)
find_git_root() {
    local dir="$1"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    echo ""
}

GIT_ROOT=$(find_git_root "$ABS_PATH")

# Determine project path (git root preferred, otherwise current directory)
if [[ -n "$GIT_ROOT" ]]; then
    PROJECT_PATH="$GIT_ROOT"
else
    PROJECT_PATH="$ABS_PATH"
fi

# Generate project hash (first 8 chars of SHA256)
PROJECT_HASH=$(echo -n "$PROJECT_PATH" | shasum -a 256 | cut -c1-8)

# Get project name (directory name)
PROJECT_NAME=$(basename "$PROJECT_PATH")

# Output based on flag
if [[ "$FLAG" == "--hash-only" ]]; then
    echo "$PROJECT_HASH"
elif [[ "$FLAG" == "--info" ]]; then
    cat <<EOF
{
  "path": "$PROJECT_PATH",
  "hash": "$PROJECT_HASH",
  "name": "$PROJECT_NAME",
  "git_root": $(if [[ -n "$GIT_ROOT" ]]; then echo "\"$GIT_ROOT\""; else echo "null"; fi),
  "is_git_repo": $(if [[ -n "$GIT_ROOT" ]]; then echo "true"; else echo "false"; fi)
}
EOF
else
    # Default output: just the hash
    echo "$PROJECT_HASH"
fi
