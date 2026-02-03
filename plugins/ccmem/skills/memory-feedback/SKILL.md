---
name: memory-feedback
description: Provide feedback on memories to adjust confidence and improve learning
---

# Memory Feedback Skill

Give feedback on memories to help the system learn and improve.

## Feedback Types

### Positive Reinforcement (Reinforce)

When a memory was helpful or correct:

```python
from memory_lib import update_memory

# Reinforce a memory (increases confidence)
update_memory(
    memory_id="2026-01-29-pnpm-preference",
    outcome="accepted"
)
```

Effect:
- Confidence +0.1
- positive_reinforcement count +1

### Negative Feedback (Correct)

When a memory was wrong or outdated:

```python
from memory_lib import update_memory

# Correct a memory (decreases confidence)
update_memory(
    memory_id="2026-01-29-npm-default",
    outcome="rejected"
)
```

Effect:
- Confidence -0.2
- negative_reinforcement count +1
- If confidence < 0.3: status changes to "under_review"

### Add New Evidence

Add new observations to a memory:

```python
from memory_lib import update_memory
from datetime import datetime

update_memory(
    memory_id="2026-01-29-pnpm-preference",
    new_evidence={
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "description": "User used pnpm again",
        "observation_id": "obs-456"
    },
    confidence_delta=0.05  # Optional small boost
)
```

### Supersede a Memory

When a new memory replaces an old one:

```python
from memory_lib import update_memory

# Mark old memory as superseded
update_memory(
    memory_id="2026-01-28-npm-default",
    outcome="superseded"
)
```

Effect:
- Status changes to "superseded"
- The superseding memory should reference this one

## CLI Feedback Commands

```bash
# Reinforce (positive feedback)
ccmem reinforce <memory_id>

# Correct (negative feedback)
ccmem correct <memory_id>

# Via sync script
python3 ~/.claude/plugins/ccmem/scripts/sync-claude-md.py --promote
```

## Automatic Feedback from Observations

The system can detect feedback signals from observations:

```python
def detect_feedback_from_observation(observation):
    """
    Analyze observation for implicit feedback.
    """
    prompt = observation.get('data', {}).get('prompt', '').lower()

    # Corrections - user says "use X instead"
    correction_patterns = [
        r'use (\w+) instead',
        r'prefer (\w+)',
        r'no, use (\w+)',
    ]

    # Check for corrections
    for pattern in correction_patterns:
        match = re.search(pattern, prompt)
        if match:
            return {
                'type': 'correction',
                'suggested': match.group(1),
                'context': prompt
            }

    # Approvals
    approval_patterns = [
        r'perfect',
        r'exactly',
        r'that worked',
        r'great',
    ]

    for pattern in approval_patterns:
        if re.search(pattern, prompt):
            return {'type': 'approval'}

    return None
```

## Confidence Decay

Memories lose confidence over time if not accessed:

```python
def apply_confidence_decay(memory, days_since_access):
    """
    Apply exponential decay to memory confidence.
    """
    import math

    # Base decay: 1% per day
    decay_factor = 0.99 ** days_since_access

    # Adjust based on feedback ratio
    meta = memory['metadata']
    positive = meta.get('positive_reinforcement', 0)
    negative = meta.get('negative_reinforcement', 0)
    total = positive + negative

    if total > 0:
        positive_ratio = positive / total
        # Memories with positive feedback decay slower
        decay_factor = decay_factor * (0.5 + 0.5 * positive_ratio)

    meta['confidence'] *= decay_factor

    if meta['confidence'] < 0.1:
        meta['status'] = 'archived'
```

## Feedback Loop in Practice

```python
# 1. System suggests based on memory
memory = load_memory("2026-01-29-pnpm-preference")
suggestion = "You might prefer using pnpm here."

# 2. User responds
user_response = "Yes, exactly!"  # or "No, I use npm now"

# 3. Detect feedback
if is_positive_response(user_response):
    update_memory(memory['id'], outcome="accepted")
elif is_negative_response(user_response):
    update_memory(memory['id'], outcome="rejected")
    # Optionally create correction memory
    create_memory(
        type="correction",
        content={
            "title": "User now prefers npm",
            "description": "User corrected pnpm preference",
            "action": "Suggest npm, not pnpm"
        },
        ...
    )
```
