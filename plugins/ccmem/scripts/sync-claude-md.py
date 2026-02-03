#!/usr/bin/env python3
"""
CLAUDE.md Synchronization Script

Handles two-way sync between memory system and CLAUDE.md files:
- Auto-promotion: High-confidence memories → CLAUDE.md
- Manual import: CLAUDE.md rules → memories

Usage:
    sync-claude-md.py --promote [project_path]     # Promote high-confidence memories
    sync-claude-md.py --import [project_path]      # Import CLAUDE.md to memories
    sync-claude-md.py --sync [project_path]        # Both directions
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from memory_lib import (
    MEMORY_DIR,
    load_config,
    load_index,
    load_memory,
    create_memory,
    list_memories,
    get_project_hash,
    format_memory_for_display
)

# Constants
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
AUTO_PROMOTE_THRESHOLD = 0.8
MIN_POSITIVE_RATIO = 0.7


def find_claude_md(project_path: Optional[str] = None) -> Optional[Path]:
    """
    Find the appropriate CLAUDE.md file.

    Priority:
    1. If project_path provided: {project}/CLAUDE.md or {project}/.claude/CLAUDE.md
    2. Walk up from current directory
    3. Global ~/.claude/CLAUDE.md
    """
    # Check project path first
    if project_path:
        project = Path(project_path).resolve()
        candidates = [
            project / ".claude" / "CLAUDE.md",
            project / "CLAUDE.md"
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

    # Walk up from current directory
    cwd = Path.cwd().resolve()
    while cwd != cwd.parent:
        candidates = [
            cwd / ".claude" / "CLAUDE.md",
            cwd / "CLAUDE.md"
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        cwd = cwd.parent

    # Fall back to global
    if GLOBAL_CLAUDE_MD.exists():
        return GLOBAL_CLAUDE_MD

    return None


def get_claude_md_for_scope(scope_type: str, project_path: Optional[str] = None) -> Path:
    """
    Get or create the CLAUDE.md path for a given scope.

    Returns the path where CLAUDE.md should be written.
    """
    if scope_type == "global":
        return GLOBAL_CLAUDE_MD

    # Project scope
    if project_path:
        project = Path(project_path).resolve()
        # Prefer project root /CLAUDE.md
        return project / "CLAUDE.md"

    # Default to global if no project path
    return GLOBAL_CLAUDE_MD


def parse_claude_md(claude_md_path: Path) -> Dict[str, Any]:
    """
    Parse a CLAUDE.md file for structured content.

    Returns dict with:
    - manual_sections: Content outside memory-sync blocks
    - auto_synced: List of auto-synced memory sections
    - all_content: Raw content
    """
    if not claude_md_path.exists():
        return {"manual_sections": "", "auto_synced": [], "all_content": ""}

    content = claude_md_path.read_text()

    # Find auto-synced sections
    auto_sync_pattern = r'<!--\s*memory-sync:\s*start\s*-->(.*?)<!--\s*memory-sync:\s*end\s*-->'
    auto_sync_matches = re.findall(auto_sync_pattern, content, re.DOTALL)

    # Extract manual sections (outside sync blocks)
    manual_content = re.sub(auto_sync_pattern, '', content, flags=re.DOTALL)

    # Parse individual memory entries from auto-synced sections
    auto_synced = []
    for section in auto_sync_matches:
        # Look for memory references: <!-- source: memory_id, confidence: X.XX -->
        mem_pattern = r'<!--\s*source:\s*(\S+),\s*confidence:\s*([\d.]+)\s*-->'
        for match in re.finditer(mem_pattern, section):
            auto_synced.append({
                "memory_id": match.group(1),
                "confidence": float(match.group(2)),
                "section": section[match.start():match.end() + 500]  # Context after
            })

    return {
        "manual_sections": manual_content.strip(),
        "auto_synced": auto_synced,
        "all_content": content
    }


def format_memory_for_claude_md(memory: Dict[str, Any]) -> str:
    """Format a single memory as a CLAUDE.md section."""
    content = memory["content"]
    meta = memory["metadata"]
    memory_id = memory["id"]
    confidence = meta.get("confidence", 0)

    lines = [
        f"<!-- source: {memory_id}, confidence: {confidence:.2f} -->",
        f"- **{content['title']}**",
        f"  - {content['description']}",
    ]

    if content.get("action"):
        lines.append(f"  - {content['action']}")

    if content.get("examples"):
        for example in content["examples"][:3]:  # Limit to 3 examples
            lines.append(f"  - Example: `{example}`")

    lines.append("")  # Empty line after
    return "\n".join(lines)


def promote_memories_to_claude_md(
    project_path: Optional[str] = None,
    dry_run: bool = False
) -> List[str]:
    """
    Promote high-confidence memories to CLAUDE.md.

    Criteria:
    - Confidence >= AUTO_PROMOTE_THRESHOLD (0.8)
    - Positive ratio >= MIN_POSITIVE_RATIO (0.7)
    - Status is "active"

    Returns list of promoted memory IDs.
    """
    # Determine scope
    if project_path:
        scope_type = "project"
        project_hash = get_project_hash(project_path)
    else:
        scope_type = "global"
        project_hash = None

    # Get memories to promote
    memories = list_memories(
        scope="all" if scope_type == "global" else "project",
        project_hash=project_hash,
        min_confidence=AUTO_PROMOTE_THRESHOLD
    )

    # Filter by positive ratio and status
    promoted = []
    for memory in memories:
        meta = memory["metadata"]
        positive = meta.get("positive_reinforcement", 0)
        negative = meta.get("negative_reinforcement", 0)
        total = positive + negative

        if total == 0:
            positive_ratio = 0.5  # Neutral if no feedback
        else:
            positive_ratio = positive / total

        if positive_ratio >= MIN_POSITIVE_RATIO and meta.get("status") == "active":
            promoted.append(memory)

    if not promoted:
        print(f"No memories meet promotion criteria for {scope_type} scope")
        return []

    # Find or create CLAUDE.md
    claude_md_path = find_claude_md(project_path) or get_claude_md_for_scope(scope_type, project_path)

    # Parse existing content
    parsed = parse_claude_md(claude_md_path)

    # Build new auto-sync section
    auto_sync_content = []
    auto_sync_content.append("<!-- memory-sync: start -->")
    auto_sync_content.append("<!-- These sections are auto-updated from high-confidence memories -->")
    auto_sync_content.append("<!-- Do not edit manually - use `memory` command or correct via feedback -->")
    auto_sync_content.append("")

    # Group memories by type
    by_type: Dict[str, List[Dict]] = {}
    for memory in promoted:
        mem_type = memory.get("type", "general")
        if mem_type not in by_type:
            by_type[mem_type] = []
        by_type[mem_type].append(memory)

    # Format each group
    type_order = ["preference", "pattern", "workflow", "project", "correction", "negative"]
    type_titles = {
        "preference": "Preferences",
        "pattern": "Patterns & Conventions",
        "workflow": "Workflows",
        "project": "Project-Specific",
        "correction": "Learned Corrections",
        "negative": "Avoid"
    }

    for mem_type in type_order:
        if mem_type in by_type:
            auto_sync_content.append(f"### {type_titles.get(mem_type, mem_type.title())}")
            auto_sync_content.append("")
            for memory in by_type[mem_type]:
                auto_sync_content.append(format_memory_for_claude_md(memory))
            auto_sync_content.append("")

    auto_sync_content.append("<!-- memory-sync: end -->")

    # Combine with manual sections
    new_content = ["# Claude Configuration"]
    new_content.append("")
    new_content.append("## Auto-Synced Memories")
    new_content.append("")
    new_content.extend(auto_sync_content)

    if parsed["manual_sections"]:
        new_content.append("")
        new_content.append("## Manual Configuration")
        new_content.append("<!-- Add your own notes below - they won't be overwritten -->")
        new_content.append("")
        new_content.append(parsed["manual_sections"])

    # Write if not dry run
    if not dry_run:
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        claude_md_path.write_text("\n".join(new_content))
        print(f"Updated {claude_md_path} with {len(promoted)} memories")
    else:
        print(f"Would update {claude_md_path} with {len(promoted)} memories")
        print("Content preview:")
        print("\n".join(new_content[:50]))

    return [m["id"] for m in promoted]


def import_claude_md_to_memories(
    project_path: Optional[str] = None,
    dry_run: bool = False
) -> List[str]:
    """
    Import rules from CLAUDE.md into memories.

    Creates memories with lower initial confidence (0.6) since they
    haven't been reinforced through the feedback system yet.

    Returns list of created memory IDs.
    """
    claude_md_path = find_claude_md(project_path)

    if not claude_md_path:
        print(f"No CLAUDE.md found for project: {project_path or 'global'}")
        return []

    # Parse the file
    parsed = parse_claude_md(claude_md_path)

    # Extract potential memories from manual sections
    # Look for bullet points that could be rules/preferences
    manual = parsed["manual_sections"]

    # Pattern: lines starting with - or * that look like rules
    rule_pattern = r'^[\s]*[-*][\s]+(.+)$'
    potential_rules = re.findall(rule_pattern, manual, re.MULTILINE)

    created_memories = []

    for rule in potential_rules:
        # Skip short or obvious non-rules
        if len(rule) < 10:
            continue

        # Determine type based on keywords
        rule_lower = rule.lower()
        if any(w in rule_lower for w in ["prefer", "always use", "never use"]):
            mem_type = "preference"
        elif any(w in rule_lower for w in ["pattern", "convention", "style"]):
            mem_type = "pattern"
        elif any(w in rule_lower for w in ["before", "after", "workflow", "process"]):
            mem_type = "workflow"
        elif any(w in rule_lower for w in ["never", "avoid", "don't"]):
            mem_type = "negative"
        else:
            mem_type = "project"

        # Extract keywords for triggers
        words = re.findall(r'\b\w{4,}\b', rule_lower)
        keywords = list(set(words))[:5]  # Top 5 unique words

        if not dry_run:
            memory_id = create_memory(
                memory_type=mem_type,
                content={
                    "title": rule[:60] + ("..." if len(rule) > 60 else ""),
                    "description": rule,
                    "action": f"Follow this rule: {rule[:100]}",
                    "examples": []
                },
                triggers={
                    "keywords": keywords,
                    "patterns": [],
                    "files": []
                },
                tags=["from-claude-md", mem_type],
                evidence=[{
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "description": f"Imported from {claude_md_path}",
                    "source": "claude-md-import"
                }],
                confidence=0.6,  # Lower confidence for imported rules
                scope_type="project" if project_path else "global",
                scope_path=project_path
            )
            created_memories.append(memory_id)
        else:
            print(f"Would create memory: {rule[:60]}...")

    if not dry_run:
        print(f"Created {len(created_memories)} memories from {claude_md_path}")

    return created_memories


def main():
    parser = argparse.ArgumentParser(
        description="Sync between memory system and CLAUDE.md"
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promote high-confidence memories to CLAUDE.md"
    )
    parser.add_argument(
        "--import",
        dest="import_",
        action="store_true",
        help="Import CLAUDE.md rules to memories"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Both directions: import then promote"
    )
    parser.add_argument(
        "--project",
        help="Project path (default: auto-detect or global)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )

    args = parser.parse_args()

    if not any([args.promote, args.import_, args.sync]):
        # Default: show status
        claude_md = find_claude_md(args.project)
        if claude_md:
            print(f"Found CLAUDE.md: {claude_md}")
            parsed = parse_claude_md(claude_md)
            print(f"Auto-synced memories: {len(parsed['auto_synced'])}")
            print(f"Manual content length: {len(parsed['manual_sections'])} chars")
        else:
            print("No CLAUDE.md found")
        return

    results = {}

    if args.sync or args.import_:
        results["imported"] = import_claude_md_to_memories(
            project_path=args.project,
            dry_run=args.dry_run
        )

    if args.sync or args.promote:
        if args.promote:
            print("WARNING: --promote is deprecated. Use 'ccmem promote' for interactive workflow.")
            print("Run: ccmem promote [--dry-run] [--project <path>]\n")
        results["promoted"] = promote_memories_to_claude_md(
            project_path=args.project,
            dry_run=args.dry_run
        )

    print("\nSync complete:")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
