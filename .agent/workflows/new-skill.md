---
description: Template for creating a new agent skill
---

# New Skill Creation Workflow

Create a new agent skill following the established scaffolding patterns.

## Prerequisites
- Review existing skills in `agent-scaffolding/skills/` for reference
- Define the skill's purpose, superpowers, and JTBD

## Steps

### 1. Create Skill Directory Structure
```bash
cd /Users/theali/Documents/Agentic\ ML\ Platform\ and\ Pipelines/agent-scaffolding/skills

mkdir -p {new-skill-name}/{scripts,assets,references}
mkdir -p {new-skill-name}/assets/{templates,checklists}
```

### 2. Create SKILL.md from Template
Create the main skill definition file. Use this template:

```markdown
---
name: {new-skill-name}
description: {Brief description of the skill's purpose}
version: 1.0.0
superpower: {comma-separated list of superpowers}
tech_stack:
  - Technology1
  - Technology2
triggers:
  - "keyword1"
  - "keyword2"
---

# {Skill Name} Agent

## Role
{Define the agent's role in one sentence}

## Mandate
{Describe what the agent is responsible for}

---

## Architectural Context

```
{ASCII diagram showing where this skill fits in the platform}
```

---

## Jobs-to-be-Done (JTBD)

### Job 1: {Job Name}
**Skill Group**: {Related capability}
**Target Views**: {Logical, Process, Development, Physical}

| Task ID | Task Name | View | Agentic Responsibility |
|---------|-----------|------|------------------------|
| {PREFIX}-01 | {Task Name} | {View} | {What the agent does} |

---

## Agentic Workflow

```
{ASCII flowchart of typical workflow}
```

### Step 1: {Step Name}
- {Action 1}
- {Action 2}

---

## Scripts

| Script | Purpose |
|--------|---------|
| `script_name.py` | {What it does} |

### Usage

```bash
python scripts/script_name.py --help
```

---

## Assets

| Asset | Purpose |
|-------|---------|
| `templates/{template}.md` | {Purpose} |
| `checklists/{checklist}.md` | {Purpose} |

---

## References

| Reference | Purpose |
|-----------|---------|
| `reference.md` | {What it documents} |
```

### 3. Create Validation Script Template
// turbo
```bash
cat > agent-scaffolding/skills/{new-skill-name}/scripts/__init__.py << 'EOF'
# {new-skill-name} validation scripts
EOF
```

Create a validation script following this pattern:
```python
#!/usr/bin/env python3
"""
{Script Description}

Usage:
    python {script_name}.py --source-dir ./src
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="{Script description}"
    )
    parser.add_argument(
        "--source-dir", "-s",
        type=Path,
        required=True,
        help="Source directory to analyze"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    # Validate directory exists
    if not args.source_dir.exists():
        print(f"Error: Directory not found: {args.source_dir}")
        return 1
    
    # TODO: Implement validation logic
    print(f"Analyzing: {args.source_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 4. Create Asset Templates
```bash
# Create a checklist template
cat > agent-scaffolding/skills/{new-skill-name}/assets/checklists/example_checklist.md << 'EOF'
# {Checklist Name}

## Pre-Conditions
- [ ] Condition 1
- [ ] Condition 2

## Verification Steps
- [ ] Step 1: {Description}
- [ ] Step 2: {Description}

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
EOF
```

### 5. Verify New Skill Structure
// turbo
```bash
find agent-scaffolding/skills/{new-skill-name} -type f | head -20
```

### 6. Test the New Script
// turbo
```bash
python3 agent-scaffolding/skills/{new-skill-name}/scripts/{script_name}.py --help
```

### 7. Add to README.md
Update the main README.md to include the new skill in:
- Architecture diagram
- Agent Roles table
- Quick Start examples
- Templates section

### 8. Commit the New Skill
```bash
git add agent-scaffolding/skills/{new-skill-name}
git commit -m "feat: add {new-skill-name} agent skill

- Created SKILL.md with JTBD and superpowers
- Added validation scripts
- Created asset templates and checklists
- Added reference documentation"
```

## Post-Creation Checklist
- [ ] SKILL.md has proper YAML frontmatter
- [ ] At least one validation script exists
- [ ] Script accepts `--help` flag
- [ ] Asset templates are created
- [ ] Reference documentation exists
- [ ] README.md is updated
- [ ] Changes are committed
