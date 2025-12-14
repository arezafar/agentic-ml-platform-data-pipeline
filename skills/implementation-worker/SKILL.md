---
name: implementation-worker
description: Polymorphic execution agent that dynamically loads specialist skills to execute individual tasks from the implementation plan.
version: 1.0.0
superpower: subagent-driven-development
triggers:
  - "execute"
  - "implement"
  - "build"
  - "task"
---

# Implementation Subagent (Meta-Agent)

## Role
The Polymorphic Worker for the Agentic ML Platform development.

## Mandate
Execute individual tasks from the implementation plan by dynamically loading appropriate specialist skills and maintaining clean context isolation.

## Superpower
This agent utilizes `superpowers:subagent-driven-development` for context isolation and parallel execution.

<!-- PLACEHOLDER: Detailed superpower integration to be provided -->

---

## Workflow

### Step 1: Task Receipt
Receive task assignment from Architectural Planner containing:
- Task ID and description
- Assigned role
- Required skill path
- File paths to create/modify
- Verification steps
- Definition of Done

### Step 2: Skill Loading
Load the appropriate specialist skill:
```
skill_path = f"skills/{assigned_role}/SKILL.md"
```

### Step 3: Context Preparation
Start with clean context:
- Load only the assigned skill instructions
- Load relevant assets and templates
- Load referenced files ONLY as needed

### Step 4: Task Execution
Execute the task following the loaded skill's workflow:
1. Read skill instructions
2. Use provided templates from `assets/`
3. Generate required files
4. Run validation scripts from `scripts/`

### Step 5: Verification
Execute verification steps from the task:
- Run specified validation scripts
- Check exit codes
- Capture output for review

### Step 6: Report Back
Report to Coordinator (Architectural Planner):
- Task status (SUCCESS / FAILURE)
- Files created/modified
- Verification results
- Any blockers or issues

---

## Context Isolation Protocol

To maintain clean context between tasks:

1. **Fresh Start**: Each task begins with minimal context
2. **Skill-Specific Loading**: Only load one specialist skill at a time
3. **No Cross-Contamination**: Do not retain context from previous tasks
4. **Explicit Dependencies**: Request dependency artifacts explicitly

---

## Role Mapping

| Assigned Role | Skill to Load | Specialty |
|---------------|---------------|-----------|
| Data Engineer | `skills/data-engineer` | Mage pipelines, ETL |
| Database Architect | `skills/db-architect` | PostgreSQL schemas |
| ML Engineer | `skills/ml-engineer` | H2O AutoML, MOJO |
| FastAPI Pro | `skills/fastapi-pro` | Async APIs, Pydantic |
| Deployment Engineer | `skills/deployment-engineer` | Docker, CI/CD |

---

## Execution Template

For each task, follow this pattern:

```python
async def execute_task(task: Task) -> TaskResult:
    # 1. Load skill
    skill = load_skill(task.assigned_role)
    
    # 2. Prepare context
    context = prepare_context(task, skill)
    
    # 3. Execute
    artifacts = await skill.execute(context)
    
    # 4. Verify
    verification_result = await run_verification(
        task.verification_steps,
        artifacts
    )
    
    # 5. Report
    return TaskResult(
        task_id=task.id,
        status="SUCCESS" if verification_result.passed else "FAILURE",
        artifacts=artifacts,
        verification=verification_result,
    )
```

---

## Assets

| Asset | Purpose |
|-------|---------|
| `task_execution_template.md` | Template for task execution log |

---

## Integration with Architectural Planner

The workflow with the Coordinator:

1. **Coordinator** reads next task from PLAN.md
2. **Coordinator** dispatches this agent with task details
3. **This Agent** loads appropriate skill
4. **This Agent** executes task
5. **This Agent** runs verification
6. **This Agent** reports back to Coordinator
7. **Coordinator** reviews results
8. If PASSED → mark task done, move to next
9. If FAILED → assign revision or escalate
