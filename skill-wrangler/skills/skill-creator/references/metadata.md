---
version: 1.0.2
created: 2026-02-02
---

# Skill Metadata

## Sources & Inspiration

1. **Anthropic skill-creator**
   - Link: https://github.com/anthropics/skills/tree/main/skills/skill-creator
   - Type: base
   - Description: Used as the foundation for this skill, extended with versioning and metadata tracking
   - Last checked: 2026-02-02

## Notes

- This skill automatically creates a metadata.md file for each new skill it initializes
- The metadata format is designed to be parseable by future plugin systems
- Sources use a structured format to enable automatic update checking

## Version History

### 1.0.2 - 2026-02-03
- Restructured metadata.md: Version History now comes last (after Sources & Notes)
- Fixed source type to "base" for Anthropic skill-creator

### 1.0.1 - 2026-02-03
- Renamed skill from skill-wrangler to skill-creator
- Updated all internal references

### 1.0.0 - 2026-02-02
- Initial skill creation
- Based on skill-creator with added versioning and source tracking
