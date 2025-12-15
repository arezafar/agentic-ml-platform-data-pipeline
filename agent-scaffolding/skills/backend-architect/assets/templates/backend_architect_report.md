# Backend Architect Report

## Report Header

**Generated**: {{date}}  
**Service**: {{service_name}}  
**Reviewed By**: Backend Architect Agent

---

## Executive Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Event Loop Lag | {{lag_ms}}ms | <10ms | ☐ |
| p99 Latency | {{p99_ms}}ms | <100ms | ☐ |
| Memory Split | {{jvm_ratio}}% JVM | 70% | ☐ |
| Circuit Open Count | {{open_count}} | 0 | ☐ |

---

## Event Loop Analysis

### Blocking Calls Detected
```
{{event_loop_output}}
```

### Remediation
- [ ] Wrap ML inference in run_in_executor
- [ ] Replace sync HTTP with httpx.AsyncClient
- [ ] Use aiofiles for file operations

---

## Memory Allocation

```
Container Limit: {{container_limit}}
├── JVM Heap (-Xmx): {{jvm_heap}} ({{jvm_ratio}}%)
└── Native Headroom: {{native_headroom}} ({{native_ratio}}%)
```

---

## Circuit Breaker Status

| Dependency | State | Failures | Last Opened |
|------------|-------|----------|-------------|
| Redis | {{redis_state}} | {{redis_failures}} | {{redis_last}} |
| PostgreSQL | {{pg_state}} | {{pg_failures}} | {{pg_last}} |

---

## GraphQL Performance

### N+1 Query Issues
```
{{dataloader_output}}
```

---

## Action Items

### Critical

1. {{critical_1}}
2. {{critical_2}}

### High Priority

1. {{high_1}}
2. {{high_2}}

---

## Sign-Off

- [ ] All blocking calls offloaded
- [ ] Memory split configured correctly
- [ ] Circuit breakers tested
- [ ] DataLoaders implemented

**Approved By**: ___________________  
**Date**: ___________________
