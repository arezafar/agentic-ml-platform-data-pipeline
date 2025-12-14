-- =============================================================================
-- PostgreSQL Schema - Hybrid JSONB Design
-- =============================================================================
-- Implements AD-003: Use JSONB for raw ingestion (Schema Flexibility)
-- 
-- Tables:
-- - raw_events: JSONB storage for heterogeneous API data
-- - prediction_logs: Inference tracking with partitioning
-- - model_versions: Model registry
-- - drift_events: Drift detection history
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_partman";

-- -----------------------------------------------------------------------------
-- Raw Events - Hybrid JSONB Schema
-- AD-003: Use JSONB over EAV for schema flexibility + performance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system VARCHAR(50) NOT NULL,
    event_type VARCHAR(50),
    payload JSONB NOT NULL  -- Heterogeneous API data
);

-- GIN index for JSONB containment queries
-- Enables: WHERE payload @> '{"region": "US"}'
CREATE INDEX IF NOT EXISTS idx_raw_events_payload_gin 
    ON raw_events USING GIN (payload);

CREATE INDEX IF NOT EXISTS idx_raw_events_source_time 
    ON raw_events (source_system, ingestion_time DESC);

-- -----------------------------------------------------------------------------
-- Prediction Logs - Partitioned Time-Series
-- Used for drift detection and model monitoring
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prediction_logs (
    id BIGSERIAL,
    request_id VARCHAR(64),
    model_version VARCHAR(50),
    features JSONB NOT NULL,
    prediction JSONB NOT NULL,
    latency_ms FLOAT,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create partitions (managed by pg_partman in production)
CREATE TABLE IF NOT EXISTS prediction_logs_default 
    PARTITION OF prediction_logs DEFAULT;

-- Index for drift detection queries
CREATE INDEX IF NOT EXISTS idx_prediction_logs_version_time 
    ON prediction_logs (model_version, created_at DESC);

-- Index for latency monitoring
CREATE INDEX IF NOT EXISTS idx_prediction_logs_latency 
    ON prediction_logs (latency_ms) WHERE latency_ms > 50;

-- -----------------------------------------------------------------------------
-- Model Versions - Registry
-- Tracks all deployed models with metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    mojo_path TEXT,
    metrics JSONB,
    config JSONB,
    training_duration_secs FLOAT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active 
    ON model_versions (is_active) WHERE is_active = TRUE;

-- -----------------------------------------------------------------------------
-- Drift Events - Monitoring History
-- Records PSI scores and triggered retraining
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drift_events (
    id SERIAL PRIMARY KEY,
    drift_scores JSONB NOT NULL,
    drifted_features TEXT[],
    max_psi FLOAT,
    threshold FLOAT DEFAULT 0.2,
    action_taken VARCHAR(50),  -- 'retrain_triggered', 'alert_sent', etc.
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drift_events_time 
    ON drift_events (detected_at DESC);

-- -----------------------------------------------------------------------------
-- Feature Store - Training Features
-- Source of truth for model training
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS features (
    entity_id VARCHAR(64) PRIMARY KEY,
    feature_vector JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_features_updated 
    ON features (updated_at DESC);

-- -----------------------------------------------------------------------------
-- Helper Functions
-- -----------------------------------------------------------------------------

-- Function to get latest prediction stats for drift detection
CREATE OR REPLACE FUNCTION get_prediction_stats(days_back INT DEFAULT 7)
RETURNS TABLE (
    feature_name TEXT,
    mean_value FLOAT,
    std_value FLOAT,
    sample_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        key AS feature_name,
        AVG((value::TEXT)::FLOAT) AS mean_value,
        STDDEV((value::TEXT)::FLOAT) AS std_value,
        COUNT(*) AS sample_count
    FROM prediction_logs, 
         jsonb_each(features) 
    WHERE created_at > NOW() - (days_back || ' days')::INTERVAL
      AND jsonb_typeof(value) = 'number'
    GROUP BY key;
END;
$$ LANGUAGE plpgsql;

-- Function to activate a model version
CREATE OR REPLACE FUNCTION activate_model(target_version VARCHAR)
RETURNS VOID AS $$
BEGIN
    -- Deactivate all models
    UPDATE model_versions SET is_active = FALSE;
    
    -- Activate target model
    UPDATE model_versions 
    SET is_active = TRUE, activated_at = NOW()
    WHERE version = target_version;
END;
$$ LANGUAGE plpgsql;
