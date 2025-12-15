# Database Optimizer Report

## Report Header

**Generated**: {{date}}  
**Database**: {{database_name}}  
**Reviewed By**: Database Optimizer Agent

---

## Executive Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Buffer Hit Ratio | {{hit_ratio}}% | >99% | ☐ |
| TOAST Ratio | {{toast_ratio}}% | <15% | ☐ |
| Query p99 | {{p99_ms}}ms | <50ms | ☐ |
| Index Bloat | {{bloat}}% | <20% | ☐ |

---

## Schema Analysis

### JSONB Key Optimization
```
{{key_analysis_output}}
```

### Column Extraction Candidates
| Key | Access Ratio | Recommendation |
|-----|--------------|----------------|
| {{key_1}} | {{ratio_1}}% | {{rec_1}} |
| {{key_2}} | {{ratio_2}}% | {{rec_2}} |

---

## Index Analysis

### GIN Index Health
```
{{gin_analysis_output}}
```

### Recommendations
- [ ] {{gin_rec_1}}
- [ ] {{gin_rec_2}}

---

## Query Performance

### Slow Queries Identified
```
{{slow_query_output}}
```

### Extended Statistics Needed
- [ ] CREATE STATISTICS on {{expr_1}}
- [ ] CREATE STATISTICS on {{expr_2}}

---

## Connection Pool

### Configuration
- Pool Size: {{pool_size}}
- CPU Cores: {{cores}}
- Optimal Size: {{optimal_size}}

### Issues
```
{{pool_analysis_output}}
```

---

## Action Items

### Critical (Block Deployment)

1. {{critical_1}}
2. {{critical_2}}

### High Priority (This Sprint)

1. {{high_1}}
2. {{high_2}}

### Medium Priority (Next Sprint)

1. {{medium_1}}

---

## Sign-Off

- [ ] All critical issues resolved
- [ ] Query latency within SLO
- [ ] Index bloat under control
- [ ] Ready for production

**Approved By**: ___________________  
**Date**: ___________________
