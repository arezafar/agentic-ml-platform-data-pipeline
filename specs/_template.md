# Skill Specification Template

Use this template to create a new skill specification. Save as `specs/{skill-name}.md`.

---

## 1. Executive Summary

**Skill Name**: {skill-name}  
**Role**: {One-line description of the agent's role}  
**Mandate**: {What the agent is responsible for}

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: {Name}
{Description of what this superpower allows the agent to perceive or analyze}

### Superpower 2: {Name}
{Description}

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- {Constraint 1}
- {Constraint 2}

### 3.2 Process View
- {Constraint 1}
- {Constraint 2}

### 3.3 Development View
- {Constraint 1}
- {Constraint 2}

### 3.4 Physical View
- {Constraint 1}
- {Constraint 2}

### 3.5 Scenario View
- {Validation scenario 1}
- {Validation scenario 2}

---

## 4. JTBD Task List

### Epic: {PREFIX}-{VIEW}-01 ({Epic Name})

**T-Shirt Size**: S/M/L/XL  
**Objective**: {What this epic achieves}  
**Dependencies**: {Other epics or None}  
**Risk**: {LOW/MEDIUM/HIGH/CRITICAL} - {Risk description}

#### Job Story (SPIN Format)
> When {Circumstance},  
> I want to {New Ability / use Superpower},  
> So that {Outcome + Emotion}.

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| {PREFIX}-01 | {Story Title} | Constraint: {Details} | ✅ {Criterion 1} ✅ {Criterion 2} |
| {PREFIX}-02 | {Story Title} | Pattern: {Details} | ✅ {Criterion 1} |

#### Spike (Optional)
**Spike ID**: SPK-{PREFIX}-01  
**Question**: {Technical question to investigate}  
**Hypothesis**: {Expected approach}  
**Timebox**: {1-3 Days}  
**Outcome**: {Expected deliverable}

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 {script_name}.py
**Purpose**: {What it does}  
**Superpower**: {Which superpower it implements}  
**Detection Logic**:
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Usage**:
```bash
python scripts/{script_name}.py --source-dir ./src
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 {Topic Name}
{Technical explanation of why this constraint matters, failure modes, remediation strategies}

### 6.2 {Topic Name}
{Technical explanation}

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: {skill-name}
superpowers:
  - superpower-1
  - superpower-2
epics:
  - id: {PREFIX}-{VIEW}-01
    name: {Epic Name}
    size: L
    stories: 3
scripts:
  - name: script_name.py
    superpower: superpower-1
checklists:
  - logical_view_{skill}.md
  - process_view_{skill}.md
references:
  - topic_1.md
  - topic_2.md
```
