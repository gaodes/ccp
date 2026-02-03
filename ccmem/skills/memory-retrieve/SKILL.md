---
name: memory-retrieve
description: Retrieve and apply memories based on context and queries
---

# Memory Retrieve Skill

Load and apply relevant memories at session start and during conversations.

## Context Loading at Session Start

```python
from memory_lib import load_session_context

# Load all relevant context for current session
context = load_session_context("/path/to/project")

# Access different memory categories
context['global_memories']       # All global memories
context['project_memories']      # Project-specific memories
context['recent_memories']       # Recently accessed memories
context['high_confidence_memories']  # Confidence > 0.8
```

## Retrieving Relevant Memories

```python
from memory_lib import search_memories, load_session_context

# Get current project context
context = load_session_context(".")
project_hash = context.get('project_hash')

# Search for relevant memories
relevant = search_memories(
    query="user is asking about testing",
    project_hash=project_hash,
    limit=5,
    min_confidence=0.5
)

# Apply the most relevant memories
for memory in relevant:
    apply_memory(memory)
```

## Formatting Memories for Display

```python
def format_memory_for_display(memory):
    """Format a single memory for display."""
    content = memory['content']
    meta = memory['metadata']

    output = f"### {content['title']}\n"
    output += f"**Confidence:** {meta['confidence']:.0%}\n"
    output += f"**Scope:** {memory['scope']['type']}\n\n"
    output += f"{content['description']}\n\n"
    output += f"**Action:** {content['action']}\n"

    if content.get('examples'):
        output += "\n**Examples:**\n"
        for ex in content['examples']:
            output += f"- {ex}\n"

    return output

def format_memories_for_context(memories):
    """Format multiple memories for injection into context."""
    if not memories:
        return ""

    output = "## Relevant Memories\n\n"
    for memory in memories:
        output += format_memory_for_display(memory)
        output += "\n---\n\n"

    return output
```

## Applying High-Confidence Memories

```python
def apply_high_confidence_memories(context):
    """
    Automatically apply memories with confidence > 0.8
    """
    high_confidence = context.get('high_confidence_memories', [])

    if not high_confidence:
        return

    print(f"Applying {len(high_confidence)} high-confidence memories:")
    for memory in high_confidence:
        print(f"  ✓ {memory['content']['title']} ({memory['metadata']['confidence']:.0%})")
        # Memory is automatically incorporated into behavior
```

## Session Start Workflow

```python
def on_session_start(project_path=None):
    """
    Complete workflow for session start memory loading.
    """
    # 1. Load context
    context = load_session_context(project_path or ".")

    # 2. Greet with context
    session_count = get_session_count()
    print(f"Back to project. {len(context['project_memories'])} project memories loaded.")

    # 3. Apply high-confidence memories
    if context['high_confidence_memories']:
        apply_high_confidence_memories(context)

    # 4. Check for evolution opportunities
    check_evolution_status()

    return context

def get_session_count():
    """Get total session count from config."""
    from memory_lib import load_config
    config = load_config()
    return config['identity']['session_count']

def check_evolution_status():
    """Check if any memory domains are ready for evolution."""
    from memory_lib import load_index
    import json

    index = load_index()

    # Count memories by tag
    tag_counts = {}
    for entry in index['memories']['global']:
        memory = load_memory(entry['id'])
        if memory:
            for tag in memory.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Check for clustering (5+ in same tag)
    ready_for_evolution = [tag for tag, count in tag_counts.items() if count >= 5]

    if ready_for_evolution:
        print(f"\n📊 Memory clustering detected in: {', '.join(ready_for_evolution)}")
        print("Run 'ccmem analyze' to evolve capabilities.")
```

## Searching During Conversation

```python
def get_relevant_memories_for_query(query, context):
    """
    Get memories relevant to a user query.
    """
    from memory_lib import search_memories

    # Search with context
    memories = search_memories(
        query=query,
        project_hash=context.get('project_hash'),
        limit=3,
        min_confidence=0.6
    )

    # Format for display
    if memories:
        return format_memories_for_context(memories)

    return None
```

## Integration Example

```python
# At session start
context = on_session_start("/Users/elche/project")

# Store context for later use
session_context = context

# Later, when user asks something
user_query = "How do I install dependencies?"
relevant = get_relevant_memories_for_query(user_query, session_context)

if relevant:
    print("Based on your preferences:")
    print(relevant)
```
