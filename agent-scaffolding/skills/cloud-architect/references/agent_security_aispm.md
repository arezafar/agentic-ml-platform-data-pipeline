# Agent Security (AISPM)

## Securing Autonomous Agents
1. **Least Privilege**: CIEM analysis to strip unused permissions
2. **Short-Lived Credentials**: OIDC tokens, no long-lived API keys
3. **Network Isolation**: Management cluster in dedicated VPC
4. **Behavioral Monitoring**: Baseline normal agent behavior, alert on deviation

## Runaway Agent Mitigation
- Circuit breakers (max actions per hour)
- Hysteresis (metrics must be stable for N minutes)
- Budget caps (hard limits on costs)
- Human-in-the-loop for critical operations
