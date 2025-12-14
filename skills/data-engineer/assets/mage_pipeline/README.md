# Agentic ML Pipeline - Mage Project

Complete pipeline template for Mage + H2O AutoML orchestration.

## Structure

```
mage_pipeline/
├── io_config.yaml           # Connection configuration
├── .env.template            # Environment variables template
├── metadata.json            # Pipeline definition
├── data_loaders/
│   ├── load_postgres.py     # PostgreSQL incremental loader
│   ├── load_api.py          # REST API with pagination
│   └── load_kafka.py        # Kafka streaming consumer
├── transformers/
│   └── clean_for_h2o.py     # H2O-compatible data prep
├── conditionals/
│   └── quality_gate.py      # Data quality validation
├── custom/
│   ├── h2o_connect.py       # H2O cluster connection
│   ├── h2o_automl.py        # AutoML training + MOJO
│   └── global_hooks.py      # Alerting (Slack/PagerDuty)
├── data_exporters/
│   ├── export_predictions.py # PostgreSQL writer
│   └── export_mojo_s3.py    # S3 artifact uploader
└── sensors/
    └── s3_file_sensor.py    # File arrival sensor
```

## Quick Start

1. Copy to your Mage project directory
2. Create `.env` from `.env.template`
3. Update `metadata.json` with your configuration
4. Deploy via: `mage start .`

## Pipeline Flow

```
[S3 Sensor] → [PostgreSQL Loader] → [Transformer] → [Quality Gate]
                                                           ↓
                                        [H2O Connect] → [AutoML Training]
                                                           ↓
                                    [Export Predictions] ←→ [Upload MOJO to S3]
```

## Environment Variables Required

- `POSTGRES_*`: Database connection
- `H2O_URL`: H2O cluster endpoint
- `AWS_*`: S3 credentials
- `SLACK_WEBHOOK_URL`: Alerting (optional)
