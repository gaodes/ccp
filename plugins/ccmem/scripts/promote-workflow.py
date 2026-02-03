#!/usr/bin/env python3
"""
ccmem Promotion Workflow
Interactive workflow for promoting memories to CLAUDE.md files.

Usage:
    promote-workflow.py --check-only              # Check if candidates exist
    promote-workflow.py --promote [--dry-run]     # Run promotion workflow
    promote-workflow.py --list-candidates         # List all candidates
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from memory_lib import (
    MEMORY_DIR,
    load_config,
    load_index,
    load_memory,
    get_project_hash,
    get_memory_path,
    archive_memory,
    get_promotion_candidates,
    log_claude_md_decision,
    ensure_directories
)

# Constants
VERSION = "1.1.0"
PLUGIN_DIR = Path(__file__).parent.parent
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
MIN_CONFIDENCE = 0.8
MIN_POSITIVE_RATIO = 0.7


def find_claude_md(project_path: Optional[str] = None, scope_type: str = "global") -> Optional[Path]:
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
    for parent in [cwd] + list(cwd.parents):
        candidates = [
            parent / ".claude" / "CLAUDE.md",
            parent / "CLAUDE.md"
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

    # Fall back to global
    if GLOBAL_CLAUDE_MD.exists():
        return GLOBAL_CLAUDE_MD

    return None


def get_claude_md_for_scope(scope_type: str, scope_path: Optional[str] = None) -> Path:
    """Get or create the CLAUDE.md path for a given scope."""
    if scope_type == "global":
        return GLOBAL_CLAUDE_MD

    # Project scope
    if scope_path:
        project = Path(scope_path).resolve()
        return project / "CLAUDE.md"

    # Default to global if no project path
    return GLOBAL_CLAUDE_MD


def extract_keywords(text: str) -> List[str]:
    """Extract significant keywords from text."""
    # Convert to lowercase, remove special chars, split
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    # Filter common stop words
    stop_words = {'the', 'and', 'for', 'use', 'use', 'when', 'with', 'should',
                  'from', 'that', 'this', 'have', 'will', 'your', 'prefer',
                  'default', 'instead', 'always', 'never', 'avoid', 'suggest'}
    return [w for w in words if w not in stop_words]


def extract_memory_titles(content: str) -> List[str]:
    """Extract existing memory titles from CLAUDE.md content."""
    titles = []
    # Match bold titles in bullet points: - **Title**
    pattern = r'^\s*[-*]\s*\*\*([^*]+)\*\*'
    for match in re.finditer(pattern, content, re.MULTILINE):
        titles.append(match.group(1).strip())
    return titles


def parse_claude_md_sections(content: str) -> List[Dict[str, Any]]:
    """Parse CLAUDE.md into sections."""
    sections = []

    # Remove markers (for backward compatibility)
    content = re.sub(r'<!--\s*memory-sync:.*?-->', '', content, flags=re.DOTALL)

    # Match section headers (## or ###)
    section_pattern = r'^(#{2,3})\s+(.+)$'

    current_section = None
    current_content = []

    for line in content.split('\n'):
        match = re.match(section_pattern, line)
        if match:
            # Save previous section
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content).strip(),
                    'level': len(match.group(1))
                })
            current_section = match.group(2).strip()
            current_content = []
        else:
            current_content.append(line)

    # Don't forget the last section
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content).strip(),
            'level': 2
        })

    return sections


def check_duplicate(memory: Dict[str, Any], claude_md_content: str) -> Tuple[str, Optional[str]]:
    """
    Check if memory is duplicate of existing content.

    Returns:
        (status, matched_title): status is 'exact', 'similar', or 'new'
    """
    existing_titles = extract_memory_titles(claude_md_content)

    memory_title = memory['content'].get('title', '').strip()

    # Exact match
    if memory_title in existing_titles:
        return 'exact', memory_title

    # Semantic similarity - keyword overlap
    memory_keywords = set(extract_keywords(memory_title))
    if not memory_keywords:
        return 'new', None

    for title in existing_titles:
        title_keywords = set(extract_keywords(title))
        if not title_keywords:
            continue

        intersection = memory_keywords & title_keywords
        union = memory_keywords | title_keywords

        if union:
            overlap = len(intersection) / len(union)
            if overlap > 0.7:  # 70% keyword overlap
                return 'similar', title

    return 'new', None


def check_overlaps(memory: Dict[str, Any], claude_md_content: str) -> List[Dict[str, Any]]:
    """Detect if memory overlaps with existing CLAUDE.md content."""
    overlaps = []

    # Get memory keywords
    memory_text = f"{memory['content'].get('title', '')} {memory['content'].get('description', '')}"
    memory_keywords = set(extract_keywords(memory_text))

    if not memory_keywords:
        return overlaps

    # Parse sections
    sections = parse_claude_md_sections(claude_md_content)

    for section in sections:
        section_keywords = set(extract_keywords(section['content']))

        # Check for keyword overlap
        overlap = memory_keywords & section_keywords
        if len(overlap) >= 2:  # At least 2 shared keywords
            overlaps.append({
                'section_title': section['title'],
                'overlap_keywords': list(overlap)[:5],  # Limit to 5
                'content_preview': section['content'][:200] + '...' if len(section['content']) > 200 else section['content']
            })

    return overlaps


def format_memory_entry(memory: Dict[str, Any]) -> str:
    """Format a memory as clean markdown (NO markers)."""
    content = memory['content']

    lines = [
        f"- **{content['title']}**",
        f"  - {content['description']}",
    ]

    if content.get('action'):
        lines.append(f"  - {content['action']}")

    if content.get('examples'):
        for example in content['examples'][:3]:  # Limit to 3 examples
            lines.append(f"  - Example: `{example}`")

    return '\n'.join(lines)


def section_exists(content: str, section_name: str) -> bool:
    """Check if a section exists in CLAUDE.md content."""
    pattern = rf'^##\s+{re.escape(section_name)}\s*$'
    return bool(re.search(pattern, content, re.MULTILINE))


def insert_into_section(content: str, section_name: str, entry: str) -> str:
    """Insert memory entry into existing section."""
    lines = content.split('\n')
    result = []
    in_target_section = False
    section_level = 2
    inserted = False

    for i, line in enumerate(lines):
        # Check if this is the target section header
        if re.match(rf'^##\s+{re.escape(section_name)}\s*$', line):
            in_target_section = True
            section_level = 2
            result.append(line)
            continue

        # Check if we're leaving the section (new section at same or higher level)
        if in_target_section and not inserted:
            next_section_match = re.match(r'^(#{2,})\s+', line)
            if next_section_match and len(next_section_match.group(1)) <= section_level:
                # Insert before this line
                result.append(entry)
                result.append('')
                inserted = True
                in_target_section = False

        result.append(line)

    # If we reached the end and haven't inserted, append
    if in_target_section and not inserted:
        result.append('')
        result.append(entry)

    return '\n'.join(result)


def create_section(content: str, section_name: str, entry: str) -> str:
    """Create a new section and add the entry."""
    # Find appropriate location - add after existing sections or at end
    sections = parse_claude_md_sections(content)

    if not sections:
        # No existing sections, add at end
        return content.rstrip() + f"\n\n## {section_name}\n\n{entry}\n"

    # Add after the last section of similar type
    type_order = ['Preferences', 'Patterns & Conventions', 'Workflows',
                  'Project-Specific', 'Learned Corrections', 'Avoid']

    if section_name in type_order:
        idx = type_order.index(section_name)
        # Find the section that should come before this one
        for i in range(idx - 1, -1, -1):
            prev_section = type_order[i]
            if section_exists(content, prev_section):
                # Insert after this section
                return insert_after_section(content, prev_section, f"\n## {section_name}\n\n{entry}")

    # Default: add at the end
    return content.rstrip() + f"\n\n## {section_name}\n\n{entry}\n"


def insert_after_section(content: str, section_name: str, text: str) -> str:
    """Insert text after a specific section."""
    lines = content.split('\n')
    result = []
    in_section = False
    section_level = 2

    for i, line in enumerate(lines):
        # Check if this is the section header
        match = re.match(rf'^(#{2,})\s+{re.escape(section_name)}\s*$', line)
        if match:
            in_section = True
            section_level = len(match.group(1))
            result.append(line)
            continue

        # Check if we're leaving the section
        if in_section:
            next_section_match = re.match(r'^(#{2,})\s+', line)
            if next_section_match and len(next_section_match.group(1)) <= section_level:
                # Insert before this line
                result.append(text)
                result.append('')
                in_section = False

        result.append(line)

    # If still in section at end, append
    if in_section:
        result.append(text)

    return '\n'.join(result)


def add_to_claude_md(memory: Dict[str, Any], target_path: Path, dry_run: bool = False) -> bool:
    """Add memory to CLAUDE.md file."""
    # Create file if doesn't exist
    if not target_path.exists():
        if dry_run:
            print(f"[DRY-RUN] Would create {target_path}")
            return True
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(f"# CLAUDE.md\n\n")

    content = target_path.read_text()

    # Determine section based on memory type
    section_map = {
        'preference': 'Preferences',
        'pattern': 'Patterns & Conventions',
        'workflow': 'Workflows',
        'project': 'Project-Specific',
        'correction': 'Learned Corrections',
        'negative': 'Avoid'
    }
    section_name = section_map.get(memory['type'], 'General')

    # Format memory entry
    memory_entry = format_memory_entry(memory)

    # Add to appropriate section
    if section_exists(content, section_name):
        new_content = insert_into_section(content, section_name, memory_entry)
    else:
        new_content = create_section(content, section_name, memory_entry)

    if dry_run:
        print(f"[DRY-RUN] Would add to {target_path}:")
        print(memory_entry)
        return True

    target_path.write_text(new_content)
    return True


def determine_target_claude_md(memory: Dict[str, Any], project_path: Optional[str] = None) -> Path:
    """Determine the correct CLAUDE.md for a memory."""
    scope = memory.get('scope', {})
    scope_type = scope.get('type', 'global')
    scope_path = scope.get('path')

    if scope_type == 'global':
        return GLOBAL_CLAUDE_MD

    # Project scope
    if scope_path:
        project = Path(scope_path).resolve()
        # Check for .claude/CLAUDE.md first
        claude_dir_md = project / ".claude" / "CLAUDE.md"
        if claude_dir_md.exists():
            return claude_dir_md
        return project / "CLAUDE.md"

    # Fallback to global
    return GLOBAL_CLAUDE_MD


def develop_memory(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Interactive memory refinement."""
    content = memory['content']

    print("\n" + "="*60)
    print("ccmem: Develop Memory")
    print("="*60)
    print("\nCurrent memory:")
    print(f"  Title: {content.get('title', '')}")
    print(f"  Description: {content.get('description', '')}")
    print(f"  Action: {content.get('action', '')}")
    if content.get('examples'):
        print(f"  Examples: {', '.join(content['examples'])}")

    print("\nEdit fields (press Enter to keep current):")

    # Get new values
    new_title = input(f"New title [{content.get('title', '')}]: ").strip()
    new_desc = input(f"New description [{content.get('description', '')}]: ").strip()
    new_action = input(f"New action [{content.get('action', '')}]: ").strip()

    examples_str = ', '.join(content.get('examples', []))
    new_examples = input(f"Add examples (comma-separated) [{examples_str}]: ").strip()

    # Update memory
    if new_title:
        content['title'] = new_title
    if new_desc:
        content['description'] = new_desc
    if new_action:
        content['action'] = new_action
    if new_examples:
        content['examples'] = [e.strip() for e in new_examples.split(',') if e.strip()]

    memory['content'] = content

    # Preview
    print("\n" + "-"*60)
    print("Preview:")
    print(format_memory_entry(memory))
    print("-"*60)

    return memory


def present_memory(memory: Dict[str, Any], candidate_num: int, total: int) -> str:
    """
    Present memory to user and get decision.

    Returns: 'add', 'develop', 'skip', 'keep', 'quit'
    """
    content = memory['content']
    meta = memory['metadata']
    scope = memory.get('scope', {})

    target_path = determine_target_claude_md(memory)

    # Check for duplicates and overlaps
    if target_path.exists():
        claude_content = target_path.read_text()
        dup_status, dup_match = check_duplicate(memory, claude_content)
        overlaps = check_overlaps(memory, claude_content)
    else:
        dup_status = 'new'
        dup_match = None
        overlaps = []

    print("\n" + "="*70)
    print(f"ccmem: Memory Candidate {candidate_num} of {total}")
    print("="*70)

    print(f"\nTitle: {content.get('title', '')}")
    print(f"Description: {content.get('description', '')}")
    if content.get('action'):
        print(f"Action: {content['action']}")
    print(f"\nConfidence: {meta.get('confidence', 0):.2f}")
    print(f"Scope: {scope.get('type', 'global')}")
    if scope.get('path'):
        print(f"Project: {scope['path']}")

    print(f"\nTarget: {target_path}")

    # Show duplicate status
    print(f"\nDuplicate check: ", end="")
    if dup_status == 'exact':
        print(f"EXACT MATCH with '{dup_match}'")
    elif dup_status == 'similar':
        print(f"SIMILAR to '{dup_match}'")
    else:
        print("No duplicates found")

    # Show overlaps
    if overlaps:
        print("\nPotential overlaps:")
        for ov in overlaps[:3]:  # Limit to 3
            print(f"  - Section '{ov['section_title']}' shares: {', '.join(ov['overlap_keywords'])}")

    print("\n" + "-"*70)
    print("Options:")
    print("  [a] Add to CLAUDE.md as-is")
    print("  [d] Develop/refine before adding")
    print("  [s] Skip (deny - won't ask again)")
    print("  [k] Keep observing (ask again later)")
    print("  [q] Quit and review remaining later")
    print("-"*70)

    while True:
        choice = input("\nChoice: ").strip().lower()

        if choice in ('a', 'add'):
            return 'add'
        elif choice in ('d', 'develop'):
            return 'develop'
        elif choice in ('s', 'skip'):
            return 'skip'
        elif choice in ('k', 'keep'):
            return 'keep'
        elif choice in ('q', 'quit'):
            return 'quit'
        else:
            print("Invalid choice. Please enter a, d, s, k, or q.")


def get_session_id() -> str:
    """Get current session ID if available."""
    session_file = MEMORY_DIR / ".current_session"
    if session_file.exists():
        return session_file.read_text().strip()
    return "unknown"


def run_promotion_workflow(
    scope: str = "all",
    project_path: Optional[str] = None,
    dry_run: bool = False,
    auto: bool = False
) -> Dict[str, int]:
    """
    Run the full promotion workflow.

    Returns:
        Dict with counts: {'added': N, 'denied': N, 'kept': N, 'developed': N}
    """
    ensure_directories()

    results = {'added': 0, 'denied': 0, 'kept': 0, 'developed': 0}

    # Get candidates
    candidates = get_promotion_candidates(scope, project_path, MIN_CONFIDENCE)

    if not candidates:
        print("ccmem: No memories meet promotion criteria.")
        return results

    print(f"ccmem: Found {len(candidates)} candidate(s) for CLAUDE.md promotion.")

    if dry_run:
        print("\n[DRY-RUN MODE - No changes will be made]\n")

    session_id = get_session_id()

    for i, memory in enumerate(candidates, 1):
        memory_id = memory['id']
        scope_info = memory.get('scope', {})
        scope_type = scope_info.get('type', 'global')
        target_path = determine_target_claude_md(memory)

        if auto:
            # Auto mode: only add if no duplicates/overlaps
            if target_path.exists():
                claude_content = target_path.read_text()
                dup_status, _ = check_duplicate(memory, claude_content)
                overlaps = check_overlaps(memory, claude_content)

                if dup_status != 'new' or overlaps:
                    print(f"[{i}/{len(candidates)}] Skipping '{memory['content']['title']}' - duplicates/overlaps detected")
                    continue

            # Add automatically
            if dry_run:
                print(f"[{i}/{len(candidates)}] [DRY-RUN] Would add '{memory['content']['title']}'")
            else:
                add_to_claude_md(memory, target_path)
                archive_memory(memory_id, 'added', 'Auto-added', session_id)
                log_claude_md_decision(memory_id, 'added', str(target_path), scope_type, 'Auto-added', session_id)
                print(f"[{i}/{len(candidates)}] Added '{memory['content']['title']}' to {target_path}")
            results['added'] += 1
            continue

        # Interactive mode
        decision = present_memory(memory, i, len(candidates))

        if decision == 'quit':
            print(f"\nccmem: Stopped. {len(candidates) - i + 1} candidate(s) remaining.")
            break

        elif decision == 'add':
            if dry_run:
                print(f"[DRY-RUN] Would add '{memory['content']['title']}'")
            else:
                add_to_claude_md(memory, target_path)
                archive_memory(memory_id, 'added', 'User approved', session_id)
                log_claude_md_decision(memory_id, 'added', str(target_path), scope_type, 'User approved', session_id)
                print(f"Added to {target_path}")
            results['added'] += 1

        elif decision == 'develop':
            memory = develop_memory(memory)

            confirm = input("\nAdd this refined memory to CLAUDE.md? [y/n]: ").strip().lower()
            if confirm in ('y', 'yes'):
                if dry_run:
                    print(f"[DRY-RUN] Would add developed memory '{memory['content']['title']}'")
                else:
                    add_to_claude_md(memory, target_path)
                    archive_memory(memory_id, 'added', 'User developed and approved', session_id)
                    log_claude_md_decision(memory_id, 'added', str(target_path), scope_type, 'User developed and approved', session_id, developed=True)
                    print(f"Added to {target_path}")
                results['added'] += 1
                results['developed'] += 1
            else:
                print("Memory not added.")
                # Don't archive - let user decide again later

        elif decision == 'skip':
            reason = input("Reason for skipping (optional): ").strip()
            if not reason:
                reason = "User chose to skip"

            if dry_run:
                print(f"[DRY-RUN] Would skip '{memory['content']['title']}'")
            else:
                archive_memory(memory_id, 'denied', reason, session_id)
                log_claude_md_decision(memory_id, 'denied', str(target_path), scope_type, reason, session_id)
                print(f"Skipped (won't ask again)")
            results['denied'] += 1

        elif decision == 'keep':
            if dry_run:
                print(f"[DRY-RUN] Would keep '{memory['content']['title']}' for observation")
            else:
                archive_memory(memory_id, 'kept_observing', 'User wants more evidence', session_id)
                log_claude_md_decision(memory_id, 'kept_observing', str(target_path), scope_type, 'User wants more evidence', session_id)
                print(f"Kept for observation (will ask again in 7 days)")
            results['kept'] += 1

    print("\n" + "="*70)
    print("ccmem: Promotion review complete")
    print(f"  Added to CLAUDE.md: {results['added']}")
    print(f"  Developed and added: {results['developed']}")
    print(f"  Skipped (denied): {results['denied']}")
    print(f"  Keep observing: {results['kept']}")
    print("="*70)

    return results


def check_candidates_only(scope: str = "all", project_path: Optional[str] = None) -> int:
    """Check if candidates exist, return count."""
    candidates = get_promotion_candidates(scope, project_path, MIN_CONFIDENCE)
    return len(candidates)


def list_candidates(scope: str = "all", project_path: Optional[str] = None):
    """List all candidates without promoting."""
    candidates = get_promotion_candidates(scope, project_path, MIN_CONFIDENCE)

    if not candidates:
        print("ccmem: No memories meet promotion criteria.")
        return

    print(f"ccmem: {len(candidates)} candidate(s) for CLAUDE.md promotion:\n")

    for i, memory in enumerate(candidates, 1):
        content = memory['content']
        meta = memory['metadata']
        scope_info = memory.get('scope', {})
        target_path = determine_target_claude_md(memory)

        print(f"{i}. {content.get('title', 'Untitled')}")
        print(f"   Description: {content.get('description', '')}")
        print(f"   Confidence: {meta.get('confidence', 0):.2f}")
        print(f"   Scope: {scope_info.get('type', 'global')}")
        print(f"   Target: {target_path}")

        # Check for duplicates
        if target_path.exists():
            dup_status, dup_match = check_duplicate(memory, target_path.read_text())
            if dup_status == 'exact':
                print(f"   WARNING: Exact duplicate of '{dup_match}'")
            elif dup_status == 'similar':
                print(f"   Note: Similar to '{dup_match}'")

        print()


def show_decisions(limit: int = 20):
    """Show recent promotion decisions."""
    from memory_lib import load_claude_md_decisions

    decisions = load_claude_md_decisions()

    if not decisions:
        print("ccmem: No promotion decisions recorded.")
        return

    # Show most recent first
    decisions.reverse()
    decisions = decisions[:limit]

    print(f"ccmem: Last {len(decisions)} promotion decision(s):\n")

    for d in decisions:
        ts = d.get('timestamp', 'unknown')[:19]  # Just date+time
        decision = d.get('decision', 'unknown')
        memory_id = d.get('memory_id', 'unknown')
        target = d.get('target_path', 'unknown')

        # Extract just filename from memory_id
        memory_name = memory_id.split('-', 2)[-1] if '-' in memory_id else memory_id

        decision_icon = {'added': '+', 'denied': '-', 'kept_observing': '~'}.get(decision, '?')

        print(f"{ts} [{decision_icon}] {memory_name}")
        print(f"    Decision: {decision}")
        if d.get('developed'):
            print(f"    Note: Memory was refined before adding")
        print(f"    Target: {target}")
        if d.get('reason'):
            print(f"    Reason: {d['reason']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="ccmem CLAUDE.md Promotion Workflow"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check if candidates exist and exit"
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Run promotion workflow"
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="List all candidates"
    )
    parser.add_argument(
        "--decisions",
        action="store_true",
        help="Show recent decisions"
    )
    parser.add_argument(
        "--scope",
        choices=["all", "global", "project"],
        default="all",
        help="Memory scope to consider (default: all)"
    )
    parser.add_argument(
        "--project",
        help="Project path (for project scope)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-promote memories with no duplicates/overlaps"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}"
    )

    args = parser.parse_args()

    if args.check_only:
        count = check_candidates_only(args.scope, args.project)
        if count > 0:
            print(f"ccmem: {count} memories ready for CLAUDE.md review.")
            print(f"Run 'ccmem promote' to review and approve them.")
        sys.exit(0 if count == 0 else 1)

    elif args.promote:
        results = run_promotion_workflow(
            scope=args.scope,
            project_path=args.project,
            dry_run=args.dry_run,
            auto=args.auto
        )
        sys.exit(0)

    elif args.list_candidates:
        list_candidates(args.scope, args.project)
        sys.exit(0)

    elif args.decisions:
        show_decisions()
        sys.exit(0)

    else:
        # Default: check and report
        count = check_candidates_only(args.scope, args.project)
        if count > 0:
            print(f"ccmem: {count} memories ready for CLAUDE.md review.")
            print(f"Run 'ccmem promote' to review and approve them.")
        else:
            print("ccmem: No memories meet promotion criteria.")
        sys.exit(0)


if __name__ == "__main__":
    main()
