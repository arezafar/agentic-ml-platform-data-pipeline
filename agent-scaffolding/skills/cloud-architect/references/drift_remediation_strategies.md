# Drift Remediation Strategies

## Severity Levels
- **CRITICAL**: Security Group changes, encryption disabled → Auto-remediate
- **HIGH**: Tag modifications, IAM changes → PR for review
- **MEDIUM/LOW**: Description changes → Log only

## Emergency Changes
Integrate with incident management to suppress auto-remediation during active response.
