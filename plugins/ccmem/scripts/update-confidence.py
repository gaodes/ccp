#!/usr/bin/env python3
"""
Confidence Adjustment Script

Adjusts memory confidence based on feedback and applies time-based decay.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from memory_lib import (
    load_config, save_config,
    load_index, save_index,
    load_memory, get_memory_path, get_project_hash,
    GLOBAL_MEMORIES_DIR, PROJECTS_DIR, FEEDBACK_FILE
)


def adjust_confidence(memory_id: str, outcome: str, confidence_delta: float = 0.0) -> bool:
    """
    Adjust memory confidence based on feedback outcome.

    Args:
        memory_id: ID of memory to update
        outcome: "accepted", "rejected", or "superseded"
        confidence_delta: Additional explicit adjustment

    Returns:
        True if updated successfully
    """
    memory = load_memory(memory_id)
    if not memory:
        print(f"Memory not found: {memory_id}")
        return False

    meta = memory["metadata"]

    if outcome == "accepted":
        # Positive feedback - boost confidence
        meta["confidence"] = min(1.0, meta["confidence"] + 0.1)
        meta["positive_reinforcement"] = meta.get("positive_reinforcement", 0) + 1
        print(f"  + Reinforced: confidence -> {meta['confidence']:.2f}")

    elif outcome == "rejected":
        # Negative feedback - significant confidence drop
        meta["confidence"] = max(0.1, meta["confidence"] - 0.2)
        meta["negative_reinforcement"] = meta.get("negative_reinforcement", 0) + 1
        print(f"  - Rejected: confidence -> {meta['confidence']:.2f}")

        # If confidence drops too low, mark for review
        if meta["confidence"] < 0.3:
            meta["status"] = "under_review"
            print(f"  ! Status changed to 'under_review'")

    elif outcome == "superseded":
        # New memory replaces this one
        meta["status"] = "superseded"
        print(f"  -> Status changed to 'superseded'")

    # Apply explicit confidence delta
    if confidence_delta:
        meta["confidence"] = min(1.0, max(0.1, meta["confidence"] + confidence_delta))
        print(f"  ~ Delta applied: confidence -> {meta['confidence']:.2f}")

    # Update access tracking
    meta["last_accessed"] = datetime.utcnow().isoformat() + "Z"
    meta["access_count"] = meta.get("access_count", 0) + 1

    # Save updated memory
    project_path = memory.get("scope", {}).get("path")
    project_hash = get_project_hash(project_path) if project_path else None
    memory_path = get_memory_path(memory_id, project_hash)

    with open(memory_path, 'w') as f:
        json.dump(memory, f, indent=2)

    # Update index
    index = load_index()
    updated = False

    for entry in index["memories"]["global"]:
        if entry["id"] == memory_id:
            entry["confidence"] = meta["confidence"]
            entry["last_accessed"] = meta["last_accessed"]
            entry["access_count"] = meta["access_count"]
            updated = True
            break

    if not updated:
        for project in index["memories"]["projects"].values():
            for entry in project.get("memories", []):
                if entry["id"] == memory_id:
                    entry["confidence"] = meta["confidence"]
                    entry["last_accessed"] = meta["last_accessed"]
                    entry["access_count"] = meta["access_count"]
                    updated = True
                    break
            if updated:
                break

    save_index(index)
    return True


def apply_confidence_decay(dry_run: bool = False) -> dict:
    """
    Apply time-based confidence decay to all memories.

    Memories lose confidence over time if not accessed or reinforced.
    Positive feedback slows decay.

    Args:
        dry_run: If True, show what would happen without making changes

    Returns:
        Statistics about the decay operation
    """
    config = load_config()
    decay_days = config["settings"].get("confidence_decay_days", 30)
    min_confidence = config["settings"].get("min_confidence", 0.1)

    stats = {
        "processed": 0,
        "decayed": 0,
        "archived": 0,
        "unchanged": 0
    }

    index = load_index()

    def process_memory(memory_id: str, entry: dict) -> None:
        memory = load_memory(memory_id)
        if not memory:
            return

        stats["processed"] += 1
        meta = memory["metadata"]

        # Skip already archived or superseded memories
        if meta.get("status") in ("archived", "superseded"):
            stats["unchanged"] += 1
            return

        # Calculate days since last access
        last_accessed_str = meta.get("last_accessed") or meta.get("created_at")
        if last_accessed_str:
            last_accessed = datetime.fromisoformat(last_accessed_str.replace("Z", "+00:00")).replace(tzinfo=None)
            days_since_access = (datetime.utcnow() - last_accessed).days
        else:
            days_since_access = decay_days  # Assume decay if no access time

        if days_since_access < 1:
            stats["unchanged"] += 1
            return

        # Calculate decay factor
        # Exponential decay: confidence *= 0.99 ^ days
        decay_factor = 0.99 ** days_since_access

        # Memories with positive feedback decay slower
        positive = meta.get("positive_reinforcement", 0)
        negative = meta.get("negative_reinforcement", 0)
        total = meta.get("access_count", 1)

        if total > 0:
            positive_ratio = positive / total
            # Scale decay factor: high positive_ratio = slower decay
            decay_factor = decay_factor * (0.5 + 0.5 * positive_ratio)

        old_confidence = meta["confidence"]
        new_confidence = old_confidence * decay_factor

        # Apply minimum confidence floor
        new_confidence = max(min_confidence, new_confidence)

        if abs(new_confidence - old_confidence) > 0.001:
            stats["decayed"] += 1

            if not dry_run:
                meta["confidence"] = round(new_confidence, 3)

                # Archive if below threshold
                if new_confidence <= min_confidence:
                    meta["status"] = "archived"
                    stats["archived"] += 1
                    print(f"  Archived: {memory_id} (confidence {old_confidence:.3f} -> {new_confidence:.3f})")
                else:
                    print(f"  Decayed: {memory_id} ({old_confidence:.3f} -> {new_confidence:.3f}, {days_since_access} days)")

                # Save memory
                project_path = memory.get("scope", {}).get("path")
                project_hash = get_project_hash(project_path) if project_path else None
                memory_path = get_memory_path(memory_id, project_hash)

                with open(memory_path, 'w') as f:
                    json.dump(memory, f, indent=2)

                # Update index entry
                entry["confidence"] = meta["confidence"]
            else:
                action = "Would archive" if new_confidence <= min_confidence else "Would decay"
                print(f"  {action}: {memory_id} ({old_confidence:.3f} -> {new_confidence:.3f}, {days_since_access} days)")
        else:
            stats["unchanged"] += 1

    # Process global memories
    for entry in index["memories"]["global"]:
        process_memory(entry["id"], entry)

    # Process project memories
    for project in index["memories"]["projects"].values():
        for entry in project.get("memories", []):
            process_memory(entry["id"], entry)

    if not dry_run:
        save_index(index)

    return stats


def process_pending_feedback() -> dict:
    """
    Process all pending feedback entries from feedback.jsonl.

    Returns:
        Statistics about processed feedback
    """
    stats = {
        "processed": 0,
        "errors": 0,
        "corrections_created": 0
    }

    if not FEEDBACK_FILE.exists():
        print("No feedback file found")
        return stats

    # Track which feedback entries have been processed
    processed_marker = Path(__file__).parent.parent / ".feedback_processed"
    last_processed = None

    if processed_marker.exists():
        with open(processed_marker, 'r') as f:
            last_processed = f.read().strip()

    entries_to_process = []

    with open(FEEDBACK_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            try:
                entry = json.loads(line)

                # Skip already processed
                if last_processed and entry.get("timestamp", "") <= last_processed:
                    continue

                entries_to_process.append(entry)
            except json.JSONDecodeError:
                stats["errors"] += 1
                continue

    if not entries_to_process:
        print("No new feedback to process")
        return stats

    print(f"Processing {len(entries_to_process)} feedback entries...")

    for entry in entries_to_process:
        memory_id = entry.get("memory_id")
        outcome = entry.get("outcome")
        feedback_type = entry.get("type")

        if not memory_id or not outcome:
            stats["errors"] += 1
            continue

        print(f"Processing: {memory_id} -> {outcome}")

        try:
            if adjust_confidence(memory_id, outcome):
                stats["processed"] += 1

                # Handle correction type feedback
                if feedback_type == "correction" and entry.get("auto_creates_memory"):
                    # Import here to avoid circular import issues
                    sys.path.insert(0, str(Path(__file__).parent / "lib"))
                    from memory_lib import create_correction_memory

                    correction_text = entry.get("feedback", "Correction applied")
                    correct_action = entry.get("correct_action", "Use the corrected approach")

                    new_id = create_correction_memory(
                        memory_id,
                        correction_text,
                        correct_action,
                        entry.get("session_id")
                    )

                    if new_id:
                        stats["corrections_created"] += 1
                        print(f"  + Created correction memory: {new_id}")
            else:
                stats["errors"] += 1

        except Exception as e:
            print(f"  Error: {e}")
            stats["errors"] += 1

    # Update last processed timestamp
    if entries_to_process:
        last_timestamp = max(e.get("timestamp", "") for e in entries_to_process)
        with open(processed_marker, 'w') as f:
            f.write(last_timestamp)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Memory confidence adjustment")
    parser.add_argument("--adjust", "-a", nargs=2, metavar=("MEMORY_ID", "OUTCOME"),
                        help="Adjust confidence for a specific memory (accepted|rejected|superseded)")
    parser.add_argument("--decay", "-d", action="store_true",
                        help="Apply confidence decay to all memories")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would happen without making changes")
    parser.add_argument("--feedback", "-f", action="store_true",
                        help="Process pending feedback from feedback.jsonl")
    parser.add_argument("--all", action="store_true",
                        help="Run all maintenance operations")

    args = parser.parse_args()

    if args.adjust:
        memory_id, outcome = args.adjust
        if outcome not in ("accepted", "rejected", "superseded"):
            print(f"Error: outcome must be accepted, rejected, or superseded")
            sys.exit(1)

        print(f"Adjusting {memory_id} with outcome: {outcome}")
        if adjust_confidence(memory_id, outcome):
            print("Done.")
        else:
            print("Failed.")
            sys.exit(1)

    elif args.decay:
        print(f"Applying confidence decay...")
        if args.dry_run:
            print("(Dry run - no changes will be made)")

        stats = apply_confidence_decay(dry_run=args.dry_run)

        print(f"\nDecay complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Decayed: {stats['decayed']}")
        print(f"  Archived: {stats['archived']}")
        print(f"  Unchanged: {stats['unchanged']}")

    elif args.feedback:
        print("Processing pending feedback...")
        stats = process_pending_feedback()

        print(f"\nFeedback processing complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Corrections created: {stats['corrections_created']}")
        print(f"  Errors: {stats['errors']}")

    elif args.all:
        print("Running all maintenance operations...\n")

        print("1. Processing feedback...")
        feedback_stats = process_pending_feedback()
        print(f"   Processed: {feedback_stats['processed']}, Corrections: {feedback_stats['corrections_created']}\n")

        print("2. Applying confidence decay...")
        decay_stats = apply_confidence_decay(dry_run=False)
        print(f"   Processed: {decay_stats['processed']}, Decayed: {decay_stats['decayed']}, Archived: {decay_stats['archived']}\n")

        print("Maintenance complete.")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  update-confidence.py -a memory-id accepted      # Reinforce a memory")
        print("  update-confidence.py -a memory-id rejected      # Reject a memory")
        print("  update-confidence.py -d                         # Apply decay")
        print("  update-confidence.py -d -n                      # Preview decay changes")
        print("  update-confidence.py -f                         # Process feedback")
        print("  update-confidence.py --all                      # Run everything")


if __name__ == "__main__":
    main()
