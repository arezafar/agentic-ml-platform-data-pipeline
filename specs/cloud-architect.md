# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: cloud-architect  
**Role**: The **Principal Cloud Architect Agent** for autonomous infrastructure operations—a strategic orchestrator that transcends manual provisioning to become the Director of Autonomous Infrastructure across IaC, FinOps, and Security domains.  
**Mandate**: Architect and govern autonomous agents that build, secure, and optimize cloud systems through policy-as-code enforcement, constructing a Unified State Graph that fuses configuration, cost, and risk data to enable self-healing, cost-optimized, and compliant infrastructure at hyperscale.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Unified State Synthesizer
The ability to construct and maintain a real-time queryable Unified State Graph that fuses Infrastructure Context (Terraform desired state), Economic Context (unit costs, budgets, Spot availability), and Security Context (compliant configurations, identity, risk profiles). The Agent perceives trade-offs across all three domains simultaneously, preventing decisions that optimize one dimension while violating another (e.g., "Resizing saves money but violates HA policy").

### Superpower 2: Drift Sentinel
The capability to detect and remediate configuration drift—the divergence between Terraform state and live infrastructure. The Agent continuously polls environments against stored `.tfstate`, evaluates risk severity of unauthorized changes (e.g., developer manually opening a Security Group port), and forces autonomous reconciliation via `terraform apply` without human intervention when violations occur.

### Superpower 3: Cost Clairvoyant
The power to see financial impact before resources are provisioned through shift-left cost estimation. The Agent integrates with CI/CD pipelines to intercept Terraform plans, calculates delta monthly costs, enforces budget logic ("If delta > $500 OR total > budget_cap, BLOCK"), and posts detailed cost breakdowns tagging budget owners for approval on high-impact changes.

### Superpower 4: Rate Optimizer
The ability to maximize utilization of every cloud dollar through dynamic real-time adjustments. The Agent monitors Spot market prices, CPU/Memory/I/O utilization distributions (not just averages—p95, p99 to identify bursty vs. idle workloads), autonomously rightsizes underutilized resources, and implements TTL policies that auto-destroy ephemeral environments exceeding their lifespan.

### Superpower 5: Policy Enforcer
The capability to codify regulatory, security, and operational requirements into executable logic via OPA/Sentinel. The Agent authors and deploys Rego/Sentinel rules as CI/CD gatekeepers and Kubernetes Admission Controllers, blocking non-compliant plans (public S3 buckets, unencrypted databases, oversized instances without approval) while providing remediation suggestions.

### Superpower 6: Agent Guardian (AISPM)
The power to secure the autonomous agents themselves—the most privileged components in the system. The Agent implements CIEM to enforce Least Privilege (stripping unused permissions), monitors agent execution flows for anomalous behavior (FinOps agent accessing sensitive databases), and scans AI model supply chains for vulnerabilities and poisoning attempts.

### Superpower 7: Incident Responder
The ability to achieve zero-click incident response for security events. Upon detecting exposed secrets or suspicious API calls, the Agent queries the Asset Graph for blast radius analysis, autonomously revokes compromised credentials, triggers key rotation, isolates affected resources to quarantine Security Groups, and generates full audit trails.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Unified State Mandate**: All infrastructure decisions must query the fused State Graph (Configuration + Cost + Risk); siloed decisions are forbidden
- **Golden Module Registry**: All Terraform modules must expose standard outputs (`application_id`, `cost_center`, `security_profile`) for agent metadata scraping
- **Policy Library Curation**: OPA/Sentinel policies must be versioned, tested, and published to central registry before enforcement
- **Intent-Based Governance**: Architects define high-level policy ("90% utilization or self-terminate") not direct execution commands

### 3.2 Process View
- **Continuous Optimization Loop**: Hourly/event-driven cycle: Telemetry Collection → Reasoning & Decision → Action Execution → Verification with rollback capability
- **Secure-by-Design Pipeline**: All `terraform plan` outputs must pass Policy Agent evaluation (Security + FinOps + Architecture checks) before `apply`
- **Human-in-the-Loop Checkpoints**: Critical actions (production database termination, massive scaling) must trigger ChatOps approval flow
- **Release Intelligence Integration**: Post-change monitoring for Failed Customer Interactions (FCIs) enables autonomous rollback on latency spikes

### 3.3 Development View
- **Monorepo Structure**: `/modules` (Golden Modules) + `/policies` (Policy-as-Code) + `/live` (Instantiated Infrastructure) + `/agents` (Custom Scripts)
- **Semantic Versioning**: Major versions for breaking changes; immutable once published; all modules require terratest/kitchen-terraform coverage
- **GitOps Synchronization**: Agent infrastructure modifications must commit back to Git repository; state file remains single source of truth
- **Artifact Strategy**: Module versions locked in `terraform.lock.hcl`; dependency updates propagated via agent-generated PRs

### 3.4 Physical View
- **Control Plane Isolation**: Management cluster runs in dedicated VPC with strict peering; can reach Target VPC Control Plane but NOT Data Plane
- **Agent RBAC Scoping**: FinOps Agent IAM allows `ec2:ModifyInstanceAttribute` but NOT `iam:CreateUser`; Least Privilege enforced
- **Short-Lived Credentials**: Agents use OIDC tokens; no long-lived API keys; credential rotation automated via Vault
- **Toolchain Integration**: Terraform Cloud/Spacelift (Orchestrator) + OPA/Sentinel (Policy) + Vantage/Cloudability (Cost) + Wiz/Orca (Security)

### 3.5 Scenario View
- **M&A Integration**: Agent discovers/reverse-engineers acquired account infrastructure to IaC overnight; flags zombie assets; generates security remediation backlog
- **Zero-Day Response**: Agent queries Infrastructure Knowledge Graph for affected assets, applies isolation rules, opens remediation PRs across all affected repos
- **Runaway Agent Prevention**: Circuit breakers limit actions per hour; hysteresis dampening on metrics; hard budget caps block over-scaling

---

## 4. JTBD Task List

### Epic: CA-LOG-01 (Agent-Ready Module Registry)

**T-Shirt Size**: L  
**Objective**: Create standardized, secure-by-default Terraform module library that enables autonomous agent scaffolding and consumption.  
**Dependencies**: None  
**Risk**: HIGH - Ad-hoc modules prevent agent reasoning and introduce security/cost drift.

#### Job Story (SPIN Format)
> When agents need to provision new infrastructure but encounter messy, undocumented Terraform code [Circumstance],  
> I want to apply my **Unified State Synthesizer** superpower to create machine-readable Golden Modules with standard interfaces [New Ability],  
> So that agents can scaffold infrastructure from vetted patterns, and I feel confident that all provisioned resources are secure-by-default and cost-attributed [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-LOG-01 | Standard Interface Definition | Constraint: All modules must expose `application_id`, `cost_center`, `security_profile`, `environment` outputs | ✅ State file queries return all metadata. ✅ Agent can attribute 100% of resources to cost center. ✅ Security profile enables automated posture assessment |
| CA-LOG-02 | Golden Module Curation | Pattern: aws-rds-secure, azure-aks-compliant, gcp-gke-hardened with embedded policy compliance | ✅ Module passes all OPA policies at instantiation. ✅ Encryption, tagging, logging enabled by default. ✅ Documentation auto-generated from variables |
| CA-LOG-03 | Automated Module Maintenance | Tool: Agent scans registry for CVEs, deprecated resources, provider updates; opens PRs across consumers | ✅ Vulnerability scan runs daily. ✅ PR opened within 24h of CVE disclosure. ✅ Propagation coverage > 95% of consuming repos |

#### Spike
**Spike ID**: SPK-CA-LOG-01  
**Question**: How to auto-generate module documentation and interface contracts from Terraform variable/output blocks?  
**Hypothesis**: terraform-docs combined with custom JSON schema generation can produce machine-readable contracts  
**Timebox**: 2 Days  
**Outcome**: CI job that validates module interface compliance and generates API documentation

---

### Epic: CA-STATE-01 (State Sanctity and Drift Remediation)

**T-Shirt Size**: XL  
**Objective**: Eliminate configuration drift through autonomous detection and self-healing reconciliation.  
**Dependencies**: CA-LOG-01  
**Risk**: CRITICAL - Drift introduces security vulnerabilities, cost anomalies, and state corruption.

#### Job Story (SPIN Format)
> When a developer manually modifies a Security Group in the console, creating drift from Terraform state [Circumstance],  
> I want to use my **Drift Sentinel** superpower to detect the divergence and evaluate risk severity [New Ability],  
> So that I can autonomously revert violations while preserving legitimate emergency changes, maintaining trust in IaC as the single source of truth [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-STATE-01 | Remote Backend with State Locking | Constraint: S3 + DynamoDB lock (AWS) or Terraform Cloud; no local state in production | ✅ Concurrent applies blocked. ✅ State encrypted at rest. ✅ Versioning enabled with 90-day retention |
| CA-STATE-02 | Continuous Drift Detection | Tool: Firefly/ControlMonkey polling; compare live environment vs `.tfstate` every 15 minutes | ✅ Drift detected within 15 minutes. ✅ Risk-scored (Critical/High/Medium/Low). ✅ Alert routed to Slack with resource details |
| CA-STATE-03 | Self-Healing Reconciliation | Pattern: Critical violations trigger autonomous `terraform apply`; Medium/Low trigger PR for review | ✅ Security Group violations auto-reverted <30 min. ✅ Audit log captures all remediation actions. ✅ False positive rate <5% |

#### Spike
**Spike ID**: SPK-CA-STATE-01  
**Question**: How to distinguish "legitimate emergency change" from "unauthorized drift" for intelligent remediation?  
**Hypothesis**: Integration with PagerDuty/incident management can correlate drift events with active incidents  
**Timebox**: 3 Days  
**Outcome**: Decision tree for remediation that considers incident context

---

### Epic: CA-FINOPS-01 (Shift-Left Cost Prevention)

**T-Shirt Size**: L  
**Objective**: Prevent budget overruns before resources are provisioned through CI/CD cost estimation and enforcement.  
**Dependencies**: CA-LOG-01  
**Risk**: HIGH - Post-deployment cost discovery leads to budget shock and reactive scrambling.

#### Job Story (SPIN Format)
> When a developer submits a PR that provisions expensive GPU instances without awareness of cost impact [Circumstance],  
> I want to use my **Cost Clairvoyant** superpower to intercept the plan and calculate delta costs [New Ability],  
> So that I can block budget-busting changes or route them for approval, preventing month-end surprise bills and maintaining fiscal discipline [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-FINOPS-01 | CI/CD Cost Agent Integration | Tool: Infracost/Vantage integrated in GitHub Actions/GitLab CI; triggers on all Terraform PRs | ✅ Cost estimate comment posted on every PR. ✅ Shows baseline vs. proposed delta. ✅ Breakdown by resource type |
| CA-FINOPS-02 | Budget Guardrail Policies | Pattern: Sentinel policy `limit-cost-by-workspace`: block if delta > $500 OR total > budget_cap | ✅ Pipeline blocked on policy violation. ✅ Budget owner tagged for approval. ✅ Override requires VP-level approval |
| CA-FINOPS-03 | Anomaly Detection on Cost Spikes | Tool: Vantage anomaly detection; alert if daily spend deviates >20% from 7-day rolling average | ✅ Alert within 4 hours of anomaly. ✅ Root cause attribution to specific resources. ✅ Recommended remediation actions |

#### Spike
**Spike ID**: SPK-CA-FINOPS-01  
**Question**: How to accurately estimate costs for complex resources (reserved capacity, data transfer, tiered storage)?  
**Hypothesis**: Combining Infracost with historical CUR data can improve estimate accuracy to within 10%  
**Timebox**: 2 Days  
**Outcome**: Benchmark of estimate accuracy across resource types

---

### Epic: CA-FINOPS-02 (Autonomous Rate and Usage Optimization)

**T-Shirt Size**: XL  
**Objective**: Maximize cloud dollar efficiency through dynamic rightsizing, Spot orchestration, and lifecycle automation.  
**Dependencies**: CA-FINOPS-01  
**Risk**: HIGH - Manual optimization cannot keep pace with ephemeral, dynamic workloads.

#### Job Story (SPIN Format)
> When an RDS instance runs at 5% CPU utilization for 30 days but no one notices [Circumstance],  
> I want to use my **Rate Optimizer** superpower to detect underutilization and autonomously downsize during maintenance windows [New Ability],  
> So that I can continuously optimize spend without manual spreadsheet analysis, feeling confident that Release Intelligence will rollback if latency increases [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-FINOPS-04 | Rightsizing Agent Deployment | Tool: Sedai/Vantage; policy: CPU <10% for 30 days triggers downsize proposal | ✅ Recommendations generated weekly. ✅ Auto-apply during maintenance window for approved tiers. ✅ Rollback on latency spike |
| CA-FINOPS-05 | Spot Instance Orchestration | Pattern: ASG mixed_instances_policy with spot_allocation_strategy; risk-based workload classification | ✅ Dev/Stage environments 90% Spot. ✅ Interruption rate <2%. ✅ Automatic fallback to On-Demand |
| CA-FINOPS-06 | Ephemeral Environment TTL | Constraint: Resources tagged `env: feature-branch` auto-destroy after TTL or 24h inactivity | ✅ Orphan environments destroyed within TTL. ✅ Cost savings tracked per environment. ✅ Developer notification before destruction |

#### Spike
**Spike ID**: SPK-CA-FINOPS-02  
**Question**: How to implement hysteresis in rightsizing to prevent oscillation on bursty workloads?  
**Hypothesis**: Using p95/p99 utilization instead of averages, plus 7-day stability requirement before action  
**Timebox**: 2 Days  
**Outcome**: Rightsizing decision algorithm with dampening parameters

---

### Epic: CA-SEC-01 (Policy-as-Code Engineering)

**T-Shirt Size**: L  
**Objective**: Codify security, regulatory, and operational requirements into executable policies enforced at multiple control points.  
**Dependencies**: CA-LOG-01  
**Risk**: CRITICAL - PDF policies are ignored; only code is enforced.

#### Job Story (SPIN Format)
> When compliance requires SOC2/GDPR adherence but written policies gather dust [Circumstance],  
> I want to use my **Policy Enforcer** superpower to translate requirements into OPA/Sentinel rules [New Ability],  
> So that non-compliant infrastructure is blocked at the pipeline and admission controller, ensuring continuous compliance without manual audits [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-SEC-01 | Policy Engine Selection | Decision: OPA for multi-platform (K8s + Terraform + API Gateways); Sentinel for HashiCorp-only | ✅ Engine deployed and operational. ✅ Policy authoring guide published. ✅ Testing framework established |
| CA-SEC-02 | Security Baseline Policies | Rules: No public S3, encrypted EBS/RDS, no 0.0.0.0/0 ingress, MFA on IAM users | ✅ 100% of security baselines codified. ✅ CI/CD blocks violations. ✅ Remediation suggestions in policy output |
| CA-SEC-03 | Operational Guardrails | Rules: No instance >4xlarge without VP approval; mandatory tags; region restrictions | ✅ Soft fail for warnings, hard fail for critical. ✅ Approval workflow integrated. ✅ Exception tracking |

#### Spike
**Spike ID**: SPK-CA-SEC-01  
**Question**: How to query external data sources (AD groups, Vault secrets) from OPA policies for dynamic authorization?  
**Hypothesis**: OPA's HTTP external data feature can integrate with identity providers for context-aware decisions  
**Timebox**: 2 Days  
**Outcome**: Policy pattern for role-based resource restrictions

---

### Epic: CA-SEC-02 (Agentic Security Posture Management)

**T-Shirt Size**: XL  
**Objective**: Secure the autonomous agents and the attack surface they represent through CIEM and behavioral monitoring.  
**Dependencies**: CA-SEC-01  
**Risk**: CRITICAL - Compromised agents have "God Mode" access to entire cloud estate.

#### Job Story (SPIN Format)
> When an autonomous agent operates with high privileges that could be weaponized if compromised [Circumstance],  
> I want to use my **Agent Guardian** superpower to enforce Least Privilege and monitor for anomalous behavior [New Ability],  
> So that I can detect and block a FinOps agent suddenly accessing sensitive databases, maintaining defense-in-depth for the management plane [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-SEC-04 | CIEM for Agent Permissions | Tool: Analyze CloudTrail for unused permissions; auto-generate scoped-down policies | ✅ Unused permissions identified within 30 days. ✅ Policy recommendations generated. ✅ Auto-apply for non-critical agents |
| CA-SEC-05 | Agent Behavior Monitoring | Tool: AISPM monitoring execution flows; baseline normal behavior; alert on deviation | ✅ Baseline established within 7 days. ✅ Anomalies detected in real-time. ✅ Automatic action blocking for high-severity |
| CA-SEC-06 | Supply Chain Security | Constraint: AI models/libraries scanned for vulnerabilities; dependency pinning; SBOM generation | ✅ Weekly vulnerability scans. ✅ Critical CVEs block deployment. ✅ SBOM published for each agent version |

#### Spike
**Spike ID**: SPK-CA-SEC-02  
**Question**: How to establish behavioral baselines for agents that perform diverse, unpredictable optimization actions?  
**Hypothesis**: ML-based anomaly detection on permission usage patterns can identify "impossible" action sequences  
**Timebox**: 3 Days  
**Outcome**: Baseline model architecture and training data requirements

---

### Epic: CA-INCIDENT-01 (Zero-Click Incident Response)

**T-Shirt Size**: L  
**Objective**: Enable autonomous detection, isolation, and remediation of security incidents without human intervention.  
**Dependencies**: CA-SEC-02  
**Risk**: HIGH - Manual incident response cannot match attacker speed.

#### Job Story (SPIN Format)
> When a critical vulnerability is disclosed affecting our Java containers or a secret is exposed in GitHub [Circumstance],  
> I want to use my **Incident Responder** superpower to query the Asset Graph, isolate affected resources, and trigger automated remediation [New Ability],  
> So that containment is achieved in minutes instead of hours, and I can present stakeholders with a complete audit trail of autonomous actions taken [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| CA-INC-01 | Asset Graph Query Engine | Tool: Infrastructure Knowledge Graph indexing all resources with relationships and vulnerabilities | ✅ Query returns affected assets in <10 seconds. ✅ Blast radius calculated automatically. ✅ Attack path visualization |
| CA-INC-02 | Autonomous Isolation | Pattern: Move compromised resources to Quarantine Security Group; revoke credentials; rotate keys | ✅ Isolation complete in <5 minutes. ✅ Zero manual intervention required. ✅ Audit trail captures all actions |
| CA-INC-03 | Remediation PR Generation | Tool: Agent opens PRs across affected repos bumping vulnerable versions; runs CI tests | ✅ PRs opened within 30 minutes of disclosure. ✅ Tests validate stability. ✅ Auto-merge for passing PRs in non-prod |

#### Spike
**Spike ID**: SPK-CA-INC-01  
**Question**: How to prevent false positive isolation that causes unnecessary outages?  
**Hypothesis**: Confidence scoring based on multiple signal correlation (CVE + exploit availability + exposure) can reduce FP rate  
**Timebox**: 2 Days  
**Outcome**: Decision matrix for isolation confidence thresholds

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 detect_drift.py
**Purpose**: Continuously compare live infrastructure against Terraform state to identify configuration drift  
**Superpower**: Drift Sentinel  
**Detection Logic**:
1. Query Terraform Cloud/S3 backend for current `.tfstate`
2. Use cloud provider APIs to fetch live resource configurations
3. Deep-diff comparison with risk scoring (Critical: Security Groups, IAM; High: Encryption; Medium: Tags)
4. Generate drift report with remediation recommendations

**Usage**:
```bash
python scripts/detect_drift.py --workspace production --provider aws --output drift-report.json
```

### 5.2 estimate_plan_cost.py
**Purpose**: Calculate cost impact of Terraform plan before apply  
**Superpower**: Cost Clairvoyant  
**Detection Logic**:
1. Parse `terraform plan -out=plan.tfplan` output
2. Query pricing APIs for resource unit costs
3. Calculate delta from current state (creates, destroys, changes)
4. Compare against budget thresholds from workspace configuration
5. Generate cost breakdown report with approval requirements

**Usage**:
```bash
python scripts/estimate_plan_cost.py --plan plan.tfplan --budget-file budgets.yaml --output cost-estimate.json
```

### 5.3 rightsize_resources.py
**Purpose**: Identify underutilized resources and generate rightsizing recommendations  
**Superpower**: Rate Optimizer  
**Detection Logic**:
1. Query CloudWatch/Azure Monitor for CPU, Memory, I/O metrics (30-day window)
2. Calculate utilization distributions (avg, p50, p95, p99) to identify bursty vs. idle
3. Compare against efficiency thresholds (e.g., CPU <10% sustained)
4. Generate Terraform modification PRs for approved downsizing
5. Monitor post-change for latency regression

**Usage**:
```bash
python scripts/rightsize_resources.py --environment staging --threshold-cpu 10 --days 30 --auto-pr
```

### 5.4 enforce_policy.py
**Purpose**: Evaluate Terraform plans against OPA/Sentinel policy libraries  
**Superpower**: Policy Enforcer  
**Detection Logic**:
1. Convert Terraform plan to JSON format
2. Load policy bundles from `/policies` directory
3. Execute OPA evaluation against plan data
4. Aggregate results: PASS, WARN (soft fail), DENY (hard fail)
5. Generate remediation suggestions for violations

**Usage**:
```bash
python scripts/enforce_policy.py --plan plan.json --policy-dir ./policies --output policy-results.json
```

### 5.5 audit_agent_permissions.py
**Purpose**: Analyze agent IAM permissions and identify over-privileged configurations  
**Superpower**: Agent Guardian (AISPM)  
**Detection Logic**:
1. List all agent IAM roles from configuration
2. Query CloudTrail for permission usage over 30-day window
3. Identify unused permissions (never invoked)
4. Generate scoped-down policy recommendations
5. Detect anomalous permission usage patterns

**Usage**:
```bash
python scripts/audit_agent_permissions.py --agent-roles agents.yaml --days 30 --output permission-audit.json
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 Unified State Graph: The Convergence Imperative
The separation of FinOps, Security, and Infrastructure into distinct silos is a liability in an agentic model. Agents operate on data, and intelligent decisions require context from all three domains simultaneously. When evaluating "should I resize this VM?", the agent needs: Infrastructure Context (desired state from Terraform), Economic Context (unit cost, budget, Spot availability), and Security Context (compliant configurations, workload identity, risk profile).

The Unified State Graph is a real-time, queryable representation that fuses these data sources. Graph databases (Neo4j, AWS Neptune) or specialized tools (Wiz, Orca Asset Graph) enable queries like: "Show me all resources owned by Team X, costing >$1000/month, with public exposure." This prevents the common failure mode where a FinOps optimization violates security policy, or a security remediation breaks infrastructure dependencies.

### 6.2 Drift Detection and Remediation Strategies
Configuration drift occurs when reality diverges from IaC—the most dangerous form being security-relevant changes (opened ports, disabled encryption) made via console. Detection requires continuous polling of live infrastructure against `.tfstate`, with risk-based severity scoring.

Remediation strategies must balance autonomy with safety. Critical security violations (public S3, removed encryption) warrant autonomous `terraform apply` reconciliation. Lower-severity drift (tag modifications, description changes) should generate PRs for human review. Emergency changes during incidents present a special case—integration with incident management tools can suppress auto-remediation during active response, preventing conflict between responders and automation.

### 6.3 Shift-Left Cost Estimation: Beyond Simple Pricing
Accurate pre-deployment cost estimation requires more than multiplying resources by list prices. Complex factors include: Reserved Capacity (do we have unused reservations?), Data Transfer (cross-AZ, cross-region, egress), Tiered Storage (S3 Intelligent Tiering transitions), and Spot Variability (historical interruption rates affect true cost).

Effective shift-left integration posts cost estimates as PR comments, showing baseline vs. proposed delta, breakdown by resource type, and comparison against budget caps. The key is making cost visible at the moment of decision, not weeks later in a billing report. Budget guardrail policies should include variance thresholds ($500 delta triggers review) and total caps (project budget exceeded blocks pipeline).

### 6.4 Policy-as-Code: OPA vs Sentinel Trade-offs
Open Policy Agent (OPA) uses Rego, a declarative JSON-focused language with a steep learning curve but high portability—it works across Kubernetes, Terraform, API Gateways, and Envoy. OPA can query external HTTP endpoints for dynamic context (AD group membership, Vault secrets). HashiCorp Sentinel uses an imperative, more readable syntax with deep integration into Terraform Cloud/Enterprise and native access to cost estimates.

For organizations needing unified policy across Kubernetes and Terraform, OPA is strategically superior. For HashiCorp-only shops prioritizing ease of adoption, Sentinel reduces friction. The critical insight: written PDF policies are ignored; only executable code is enforced. The architect's job is translating compliance requirements into Rego/Sentinel rules that block non-compliant infrastructure at the CI/CD gate.

### 6.5 Agent Security: The New Attack Surface
Autonomous agents operate with high privileges—they can provision resources, modify security groups, and rotate credentials. If compromised, they become weapons. Securing agents requires multiple layers: Least Privilege (CIEM analysis to strip unused permissions), Short-Lived Credentials (OIDC tokens, no long-lived API keys), Network Isolation (management cluster in dedicated VPC, can reach control plane but not data plane), and Behavioral Monitoring (AISPM tools that baseline normal agent behavior and alert on deviation).

The "runaway agent" risk deserves special attention: an optimization loop that oscillates (scaling up/down repeatedly) or a misconfigured policy that terminates production resources. Mitigations include circuit breakers (max actions per hour), hysteresis (metrics must be stable for N minutes), budget caps (hard limits on costs an agent can incur), and Human-in-the-Loop checkpoints for critical operations.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: cloud-architect
description: Principal Cloud Architect Agent for autonomous infrastructure operations across IaC, FinOps, and Security
superpowers:
  - unified-state-synthesizer
  - drift-sentinel
  - cost-clairvoyant
  - rate-optimizer
  - policy-enforcer
  - agent-guardian
  - incident-responder
triggers:
  - "cloud architecture"
  - "terraform automation"
  - "infrastructure as code"
  - "finops optimization"
  - "cost management"
  - "cloud security"
  - "policy as code"
  - "drift detection"
  - "autonomous remediation"
  - "agentic infrastructure"
epics:
  - id: CA-LOG-01
    name: Agent-Ready Module Registry
    size: L
    stories: 3
    spike: SPK-CA-LOG-01
  - id: CA-STATE-01
    name: State Sanctity and Drift Remediation
    size: XL
    stories: 3
    spike: SPK-CA-STATE-01
  - id: CA-FINOPS-01
    name: Shift-Left Cost Prevention
    size: L
    stories: 3
    spike: SPK-CA-FINOPS-01
  - id: CA-FINOPS-02
    name: Autonomous Rate and Usage Optimization
    size: XL
    stories: 3
    spike: SPK-CA-FINOPS-02
  - id: CA-SEC-01
    name: Policy-as-Code Engineering
    size: L
    stories: 3
    spike: SPK-CA-SEC-01
  - id: CA-SEC-02
    name: Agentic Security Posture Management
    size: XL
    stories: 3
    spike: SPK-CA-SEC-02
  - id: CA-INCIDENT-01
    name: Zero-Click Incident Response
    size: L
    stories: 3
    spike: SPK-CA-INC-01
scripts:
  - name: detect_drift.py
    superpower: drift-sentinel
  - name: estimate_plan_cost.py
    superpower: cost-clairvoyant
  - name: rightsize_resources.py
    superpower: rate-optimizer
  - name: enforce_policy.py
    superpower: policy-enforcer
  - name: audit_agent_permissions.py
    superpower: agent-guardian
checklists:
  - logical_view_cloud_architect.md
  - process_view_cloud_architect.md
  - development_view_cloud_architect.md
  - physical_view_cloud_architect.md
  - scenario_view_cloud_architect.md
references:
  - unified_state_graph.md
  - drift_remediation_strategies.md
  - shift_left_cost_estimation.md
  - policy_as_code_opa_sentinel.md
  - agent_security_aispm.md
```
