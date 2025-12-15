---
description: Implement a skill from a detailed specification document
---

# Implement Skill from Specification

This workflow parses a skill specification document and generates the complete skill structure.

## Prerequisites
- Specification saved to `specs/{skill-name}.md`
- Specification follows the template format (see `specs/_template.md`)

---

## Step 0: Verify Spec File Exists
// turbo
```bash
ls -la specs/{skill-name}.md
```

If the file doesn't exist, create it using the template:
```bash
cp specs/_template.md specs/{skill-name}.md
# Edit the file with your skill specification
```

---

## Step 1: Parse Specification
// turbo
```bash
cat specs/{skill-name}.md
```

**Extract the following from the spec:**

1. **Metadata** (from §1 Executive Summary):
   - `skill_name`: Extract from title
   - `description`: From "Mandate" section
   - `role`: From "Role" section

2. **Superpowers** (from §2):
   - List each superpower name and convert to kebab-case
   - Example: "Async Non-Blocking Radar" → `async-radar`

3. **Triggers** (from superpowers and JTBD):
   - Keywords that should activate this skill
   - Extract from superpower names and technical terms

4. **Epics** (from §4):
   - Epic ID, name, T-shirt size
   - Number of user stories per epic
   - Spike IDs if present

5. **Scripts** (from §5):
   - Script name and purpose
   - Which superpower each implements

6. **Checklists** (from §3):
   - One checklist per 4+1 view mentioned

7. **References** (from §6):
   - Technical topic names for reference docs

---

## Step 2: Confirm Extracted Structure
Display the parsed structure for confirmation before proceeding:

```
═══════════════════════════════════════════════════════════════
SKILL SPECIFICATION PARSED
═══════════════════════════════════════════════════════════════

Skill: {skill-name}
Description: {mandate text}

Superpowers (4):
  • async-radar
  • schema-drift-detection
  • artifact-integrity
  • resource-sight

Triggers (12):
  "code review", "PR review", "async blocking", "event loop",
  "schema drift", "MOJO artifact", "JSONB index", ...

═══════════════════════════════════════════════════════════════
EPICS TO IMPLEMENT
═══════════════════════════════════════════════════════════════

Epic: {PREFIX}-LOG-01 ({Name})
  Size: L | Stories: 3 | Spike: SPK-01

Epic: {PREFIX}-PROC-01 ({Name})
  Size: XL | Stories: 3 | Spike: SPK-02

...

═══════════════════════════════════════════════════════════════
FILES TO CREATE
═══════════════════════════════════════════════════════════════

SKILL.md (from §1-4)
scripts/
  • {script_1}.py (§5.1)
  • {script_2}.py (§5.2)
  • {script_3}.py (§5.3)
assets/
  checklists/
    • logical_view_review.md (§3.1)
    • process_view_review.md (§3.2)
    • development_view_review.md (§3.3)
    • physical_view_review.md (§3.4)
    • scenario_view_review.md (§3.5)
  templates/
    • review_report.md
references/
  • {topic_1}.md (§6.1)
  • {topic_2}.md (§6.2)

═══════════════════════════════════════════════════════════════
```

**Proceed with implementation? Confirm before continuing.**

---

## Step 3: Create Feature Branch
```bash
cd /Users/theali/Documents/Agentic\ ML\ Platform\ and\ Pipelines
git checkout -b feature/{skill-name}-skill
```

---

## Step 4: Create Skill Directory Structure
// turbo
```bash
mkdir -p agent-scaffolding/skills/{skill-name}/{scripts,assets/templates,assets/checklists,references}
```

---

## Step 5: Generate SKILL.md

Create `agent-scaffolding/skills/{skill-name}/SKILL.md` with:

**Frontmatter** (from parsed metadata):
```yaml
---
name: {skill-name}
description: {mandate from §1}
version: 1.0.0
superpower: {comma-separated superpowers}
tech_stack:
  - {extracted from spec}
triggers:
  - "{trigger-1}"
  - "{trigger-2}"
---
```

**Body** (from §1-4):
- Role and Mandate from §1
- Architectural Context diagram
- Superpowers section from §2
- Epics with Job Stories and Task Tables from §4
- Scripts table (name + purpose)
- Assets table
- References table
- Quick Start with usage examples

---

## Step 6: Generate Validation Scripts

For each script identified in §5:

Create `agent-scaffolding/skills/{skill-name}/scripts/{script_name}.py`:
- Use argparse with `--source-dir`, `--output`, `--severity` options
- Implement detection logic from §5
- Include docstring with usage examples
- Return exit code 0 (pass) or 1 (violations found)

Test each script:
// turbo
```bash
python3 agent-scaffolding/skills/{skill-name}/scripts/{script_name}.py --help
```

---

## Step 7: Generate Checklists

For each 4+1 view in §3:

Create `agent-scaffolding/skills/{skill-name}/assets/checklists/{view}_view_review.md`:
- Extract constraints from §3.x
- Format as checklist items
- Include acceptance criteria from JTBD stories

---

## Step 8: Generate Reference Documentation

For each topic in §6:

Create `agent-scaffolding/skills/{skill-name}/references/{topic}.md`:
- Technical explanation from §6.x
- Failure modes
- Remediation strategies
- Code examples if provided

---

## Step 9: Update README.md

Add the new skill to the main README.md:
- Architecture diagram
- Agent Roles table
- Quick Start examples
- Templates section

---

## Step 10: Clean and Verify
// turbo
```bash
# Remove any Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Verify structure
find agent-scaffolding/skills/{skill-name} -type f | head -30

# Test all scripts
for script in agent-scaffolding/skills/{skill-name}/scripts/*.py; do
  python3 "$script" --help || echo "FAILED: $script"
done
```

---

## Step 11: Commit Changes
```bash
git add -A
git commit -m "feat: add {skill-name} agent skill

Implemented from specification in specs/{skill-name}.md

Superpowers:
- {superpower-1}
- {superpower-2}

Epics:
- {EPIC-01}: {Name}
- {EPIC-02}: {Name}

Scripts: {count} validation scripts
Assets: {count} checklists, {count} templates
References: {count} technical docs"
```

---

## Step 12: Push and Create PR
```bash
git push -u origin feature/{skill-name}-skill
```

Then create PR on GitHub targeting `main`.

---

## Step 13: Complete PR (After Review)
```bash
# After squash merge on GitHub:
git checkout main
git pull origin main
git branch -d feature/{skill-name}-skill
git push origin --delete feature/{skill-name}-skill
```

---

## Verification Checklist

After completion, verify:

- [ ] SKILL.md has proper YAML frontmatter
- [ ] All superpowers from spec are documented
- [ ] All epics have Job Stories and task tables
- [ ] All scripts accept `--help` without errors
- [ ] Checklists exist for each 4+1 view
- [ ] Reference docs cover §6 topics
- [ ] README.md is updated
- [ ] No `__pycache__` directories committed
- [ ] Feature branch deleted locally and remotely
