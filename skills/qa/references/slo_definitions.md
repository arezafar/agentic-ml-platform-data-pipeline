# SLO/SLI Definitions

## Overview

Service Level Objectives (SLOs) and Service Level Indicators (SLIs) define the reliability targets for the Agentic ML Platform. This document specifies the metrics and thresholds used for quality gating.

---

## Service Level Indicators (SLIs)

### 1. Latency SLI

**Definition**: The proportion of valid inference requests served within the latency threshold.

**Measurement Point**: Load balancer / API gateway response time histogram.

**Formula**:
```
Latency SLI = count(requests where response_time < threshold) / total_requests × 100
```

**Thresholds**:
| Percentile | Threshold | Use Case |
|------------|-----------|----------|
| p50 (median) | < 25ms | Baseline performance |
| p95 | < 40ms | Typical user experience |
| p99 | < 50ms | Tail latency (SLO target) |
| p99.9 | < 100ms | Extreme outliers |

---

### 2. Availability SLI

**Definition**: The proportion of requests that return a successful (non-5xx) response.

**Formula**:
```
Availability SLI = (total_requests - count(5xx_responses)) / total_requests × 100
```

**Exclusions**:
- 4xx errors (client errors) are NOT counted as failures
- Health check requests (/health) are excluded from calculations
- Intentional errors (e.g., validation failures) are excluded

**Target**: 99.9% availability (Three Nines)

---

### 3. Freshness SLI (ETL Pipeline)

**Definition**: The time elapsed between data arrival in the source system and its availability in the Feature Store.

**Measurement**:
```
Freshness = timestamp_available_in_feature_store - timestamp_arrived_at_source
```

**Implementation**:
```python
# Record ingestion timestamp
ingestion_time = datetime.utcnow()

# After feature store write
feature_store_time = datetime.utcnow()
freshness_seconds = (feature_store_time - ingestion_time).total_seconds()

FRESHNESS_HISTOGRAM.observe(freshness_seconds)
```

**Target**: < 15 minutes for 99% of data

---

### 4. Throughput SLI

**Definition**: The number of successful requests processed per second.

**Formula**:
```
Throughput SLI = count(successful_requests in window) / window_duration_seconds
```

**Target**: 1000 requests/second sustained

---

## Service Level Objectives (SLOs)

### Production SLOs

| SLO | SLI | Target | Measurement Window |
|-----|-----|--------|-------------------|
| Latency | p99 Response Time | < 50ms | Rolling 5-minute |
| Availability | Success Rate | 99.9% | Rolling 30-day |
| Throughput | RPS | ≥ 1000 | Peak hour average |
| Freshness | ETL Lag | < 15 min (p99) | Rolling 24-hour |

### Error Budget

**Formula**:
```
Error Budget = 100% - SLO Target

Example: 99.9% availability SLO → 0.1% error budget
         In 30 days: 0.001 × 30 × 24 × 60 = 43.2 minutes of downtime allowed
```

**Error Budget Policy**:
- If budget exhausted: Feature freeze, focus on reliability
- If budget healthy: Proceed with deployments

---

## Monitoring Implementation

### Prometheus Metrics

```yaml
# Latency histogram
- name: http_request_duration_seconds
  type: histogram
  help: Request latency in seconds
  buckets: [0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0]

# Request counter (for availability)
- name: http_requests_total
  type: counter
  labels: [method, endpoint, status_code]

# Throughput gauge
- name: http_requests_per_second
  type: gauge
  help: Current request rate
```

### Prometheus Recording Rules

```yaml
groups:
  - name: slo_recording
    rules:
      # P99 latency over 5 minutes
      - record: slo:http_request_duration_seconds:p99_5m
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
      
      # Availability over 30 days
      - record: slo:http_availability:30d
        expr: |
          1 - (
            sum(rate(http_requests_total{status_code=~"5.."}[30d]))
            /
            sum(rate(http_requests_total[30d]))
          )
```

### Grafana Dashboard Panels

1. **Latency Panel**: Line chart of p50, p95, p99 over time
2. **Availability Panel**: Single stat showing current availability %
3. **Error Budget Panel**: Gauge showing remaining budget
4. **Throughput Panel**: Line chart of requests/second

---

## Alerting Rules

### P99 Latency Alert

```yaml
- alert: HighP99Latency
  expr: slo:http_request_duration_seconds:p99_5m > 0.050
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 latency exceeds 50ms SLO"
    description: "P99 latency is {{ $value | humanizeDuration }}"
```

### Availability Alert

```yaml
- alert: AvailabilityDegraded
  expr: slo:http_availability:1h < 0.999
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Availability below 99.9% SLO"
    description: "Current availability: {{ $value | humanizePercentage }}"
```

### Error Budget Burn Rate

```yaml
- alert: ErrorBudgetBurnRateHigh
  expr: |
    (
      1 - sum(rate(http_requests_total{status_code!~"5.."}[1h]))
          / sum(rate(http_requests_total[1h]))
    ) / 0.001 > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Error budget burn rate is 10x normal"
```

---

## CI/CD SLO Gating

### Pre-Deployment Gate

```yaml
# GitHub Actions workflow
- name: Run Load Test
  run: |
    locust -f locustfile.py --headless --users 100 --spawn-rate 10 \
           --run-time 2m --csv results

- name: Check SLO
  run: |
    python scripts/run_slo_gate.py \
      --results results_stats.csv \
      --p99-threshold 50 \
      --error-rate 0.001
```

### Post-Deployment Validation

```yaml
- name: Canary Health Check
  run: |
    # Wait for deployment
    sleep 60
    
    # Check SLO metrics
    LATENCY=$(curl -s "http://prometheus/api/v1/query?query=slo:http_request_duration_seconds:p99_5m" | jq '.data.result[0].value[1]')
    
    if (( $(echo "$LATENCY > 0.050" | bc -l) )); then
      echo "SLO violated, triggering rollback"
      kubectl rollout undo deployment/inference-api
      exit 1
    fi
```

---

## Task Reference

| Task ID | Description |
|---------|-------------|
| SLO-CI-01 | Implement SLO Gating in Pipeline |
| SLO-CI-02 | Verify Alerting Rules |
| ST-LOAD-01 | High-Concurrency Stress Test (1000 req/s) |
