#!/usr/bin/env python3
"""
Build the search index from all memory files.
Usage: python build-index.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from memory_lib import build_search_index, SEARCH_INDEX_FILE

if __name__ == "__main__":
    print("Building search index...")
    index = build_search_index()
    print(f"Indexed {len(index['terms'])} terms and {len(index['tags'])} tags")
    print(f"Index saved to {SEARCH_INDEX_FILE}")
