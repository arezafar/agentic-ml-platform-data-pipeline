# Model Card: {{ model_name }}

## Model Details

| Attribute | Value |
|-----------|-------|
| **Model Name** | {{ model_name }} |
| **Version** | {{ version }} |
| **Type** | {{ model_type }} |
| **Framework** | H2O.ai {{ h2o_version }} |
| **Created** | {{ created_at }} |
| **Created By** | {{ created_by }} |

### Description

{{ model_description }}

---

## Intended Use

### Primary Use Case

{{ primary_use_case }}

### Users

{{ intended_users }}

### Out-of-Scope Uses

{{ out_of_scope }}

---

## Training Data

### Data Source

{{ data_source }}

### Feature Store Reference

| Attribute | Value |
|-----------|-------|
| Feature Set | {{ feature_set }} |
| Feature Version | {{ feature_version }} |
| Training Partition | {{ training_partition }} |
| Sample Size | {{ sample_size }} |
| Date Range | {{ data_date_range }} |

### Feature Summary

| Feature | Type | Description |
|---------|------|-------------|
{{ feature_table }}

---

## Model Performance

### Primary Metrics

| Metric | Training | Validation | Test |
|--------|----------|------------|------|
{{ metrics_table }}

### Performance by Segment

{{ segment_performance }}

---

## Hyperparameters

```json
{{ hyperparameters_json }}
```

---

## Ethical Considerations

### Bias Analysis

{{ bias_analysis }}

### Fairness Metrics

{{ fairness_metrics }}

---

## Deployment

### Serving Configuration

| Attribute | Value |
|-----------|-------|
| Artifact Path | {{ artifact_path }} |
| Artifact Type | MOJO |
| Serving Endpoint | {{ serving_endpoint }} |
| Expected Latency | {{ expected_latency }} |

### Dependencies

- h2o-genmodel.jar (included with MOJO)
- Java Runtime 8+
- FastAPI serving layer

---

## Maintenance

### Monitoring

- Prediction distribution drift
- Feature drift detection
- Performance degradation alerts

### Retraining Schedule

{{ retraining_schedule }}

### Model Registry Entry

| Attribute | Value |
|-----------|-------|
| Registry ID | {{ registry_id }} |
| Status | {{ model_status }} |
| Lineage | {{ lineage_info }} |

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
{{ changelog }}

---

## Contact

**Model Owner**: {{ model_owner }}
**Team**: {{ team }}
**Email**: {{ contact_email }}
