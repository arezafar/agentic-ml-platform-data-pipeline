# SPIN Job Story Template

The SPIN format structures Job Stories to capture the complete context of an agentic task:
- **S**ituation/Circumstance
- **P**roblem/New Ability  
- **I**mpact/Success Criteria
- **N**eed/Emotion

---

## Template

```
When [CIRCUMSTANCE: specific situation or trigger],
I want to [NEW ABILITY: capability or action to take],
So that [OUTCOME: measurable success] and [EMOTION: feeling or confidence state].
```

---

## Examples

### Logical View Job Story
```
When a developer submits a database migration script involving feature data,
I want to use my Schema Drift Detector superpower to verify JSONB types and GIN indexes,
So that query latency remains stable as data volume grows and I feel confident in the system's long-term scalability.
```

### Process View Job Story
```
When reviewing a Pull Request for a new inference endpoint or data integration,
I want to apply my Async Non-Blocking Radar to identify synchronous calls in async functions,
So that the API remains responsive under high load and I avoid the anxiety of production outages.
```

### Development View Job Story
```
When a data scientist modifies the model training pipeline in Mage,
I want to use my Artifact Integrity Scanner to verify that the output is a MOJO zip file,
So that the deployment remains lightweight and compatible with the C++ runtime, giving me peace of mind during deployments.
```

### Physical View Job Story
```
When a DevOps engineer updates the Docker Compose or Kubernetes manifests,
I want to use my Resource Isolation Sight to calculate the ratio between JVM Heap and Container Memory limits,
So that I can ensure sufficient overhead for Native memory, preventing OOM kills and ensuring system stability.
```

### Scenario View Job Story
```
When a new feature is ready for release,
I want to see evidence of successful end-to-end scenario execution,
So that I can verify that Drift Handling and Zero-Downtime Update mechanisms function correctly in production.
```

---

## Writing Guidelines

### Circumstance (When...)
- Be specific about the trigger event
- Include the actor (developer, data scientist, DevOps engineer)
- Reference the artifact being changed (migration, endpoint, pipeline, manifest)

### New Ability (I want to...)
- Reference the specific "Superpower" being applied
- Describe the detection or verification capability
- Use active verbs (verify, detect, calculate, identify)

### Outcome (So that...)
- Include a measurable success criterion
- Reference system quality attributes (latency, stability, scalability)

### Emotion (and I feel...)
- Express the confidence state after successful execution
- Common emotions: confident, peace of mind, assured, secure
- Or negative emotions avoided: anxiety, fear, uncertainty

---

## Anti-Patterns

### ❌ Too Vague
```
When code is submitted,
I want to review it,
So that it is correct.
```

### ❌ Missing Emotion
```
When a developer submits code,
I want to check for blocking calls,
So that the API is fast.
```

### ❌ Missing Measurable Outcome
```
When reviewing code,
I want to use my superpowers,
So that I feel good.
```

---

## Checklist

- [ ] Circumstance specifies WHO and WHAT artifact
- [ ] New Ability references a specific Superpower
- [ ] Outcome includes measurable quality attribute
- [ ] Emotion expresses confidence state
- [ ] Story is specific enough to validate with acceptance criteria
