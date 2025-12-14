-- =============================================================================
-- PostgreSQL Schema - Hybrid JSONB Design with Time-Travel
-- =============================================================================
-- 4+1 Architectural View Model - Logical View Implementation
--
-- LOG-01-01: Feature Store with JSONB + GIN indexing
-- LOG-01-02: Time-Series partitioning with pg_partman
-- LOG-01-03: Model Registry schema with versioning
--
-- Tables:
-- - features: Time-travel feature store (entity_id, event_time, feature_vector)
-- - raw_events: JSONB storage for heterogeneous API data
-- - prediction_logs: Inference tracking with partitioning
-- - model_versions: Model registry with lineage
-- - drift_events: Drift detection history
--
-- Extensions Required:
-- - uuid-ossp: UUID generation
-- - pg_partman: Automatic partition management
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_partman";

-- =============================================================================
-- LOG-01-01: Feature Store Schema (Hybrid JSONB with GIN Indexing)
-- =============================================================================
-- Time-travel capability: Reconstruct feature state at any point in history
-- JSONB + GIN enables efficient schema-on-read queries
-- =============================================================================

CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL,
    entity_id VARCHAR(64) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feature_vector JSONB NOT NULL,
    feature_version VARCHAR(20) DEFAULT 'v1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, event_time)
) PARTITION BY RANGE (event_time);

-- Create default partition (pg_partman will manage others)
CREATE TABLE IF NOT EXISTS features_default 
    PARTITION OF features DEFAULT;

-- GIN index for JSONB containment queries
-- Enables: WHERE feature_vector @> '{"churn_risk": "high"}'
CREATE INDEX IF NOT EXISTS idx_features_vector_gin 
    ON features USING GIN (feature_vector);

-- B-tree index for entity lookups with time range
CREATE INDEX IF NOT EXISTS idx_features_entity_time 
    ON features (entity_id, event_time DESC);

-- Partial index for latest features per entity
CREATE INDEX IF NOT EXISTS idx_features_latest 
    ON features (entity_id, event_time DESC) 
    WHERE event_time > NOW() - INTERVAL '7 days';

-- =============================================================================
-- LOG-01-02: pg_partman Configuration for Time-Series Partitioning
-- =============================================================================
-- Weekly partitions with automatic creation and maintenance
-- Reduces query time via partition pruning
-- =============================================================================

SELECT partman.create_parent(
    p_parent_table => 'public.features',
    p_control => 'event_time',
    p_type => 'native',
    p_interval => 'weekly',
    p_premake => 4,
    p_start_partition => (NOW() - INTERVAL '1 month')::text
);

-- Configure partition maintenance
UPDATE partman.part_config 
SET 
    retention = '90 days',              -- Keep 90 days of history
    retention_keep_table = false,        -- Drop old partitions
    infinite_time_partitions = true
WHERE parent_table = 'public.features';

-- =============================================================================
-- Raw Events - Schema-Flexible Ingestion
-- =============================================================================
-- Heterogeneous API data with minimal schema constraints
-- GIN index enables efficient JSON path queries
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system VARCHAR(50) NOT NULL,
    event_type VARCHAR(50),
    payload JSONB NOT NULL
);

-- GIN index for JSONB containment queries
CREATE INDEX IF NOT EXISTS idx_raw_events_payload_gin 
    ON raw_events USING GIN (payload);

CREATE INDEX IF NOT EXISTS idx_raw_events_source_time 
    ON raw_events (source_system, ingestion_time DESC);

-- =============================================================================
-- Prediction Logs - Partitioned Time-Series for Drift Detection
-- =============================================================================
-- PROC-02: Tracks all inference requests for monitoring
-- SCN-01-02: Source data for drift detection sensors
-- =============================================================================

CREATE TABLE IF NOT EXISTS prediction_logs (
    id BIGSERIAL,
    request_id VARCHAR(64),
    model_version VARCHAR(50) NOT NULL,
    features JSONB NOT NULL,
    prediction JSONB NOT NULL,
    confidence FLOAT,
    latency_ms FLOAT,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create default partition
CREATE TABLE IF NOT EXISTS prediction_logs_default 
    PARTITION OF prediction_logs DEFAULT;

-- Configure pg_partman for prediction logs (daily partitions)
SELECT partman.create_parent(
    p_parent_table => 'public.prediction_logs',
    p_control => 'created_at',
    p_type => 'native',
    p_interval => 'daily',
    p_premake => 7,
    p_start_partition => (NOW() - INTERVAL '7 days')::text
);

-- Indexes for drift detection and monitoring
CREATE INDEX IF NOT EXISTS idx_prediction_logs_version_time 
    ON prediction_logs (model_version, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_latency 
    ON prediction_logs (latency_ms) 
    WHERE latency_ms > 50;  -- Slow query detection

-- =============================================================================
-- LOG-01-03: Model Registry - Version Control for ML Artifacts
-- =============================================================================
-- SCN-01-01: Enables zero-downtime model hot-swap
-- Tracks MOJO path, metrics, and activation state
-- =============================================================================

CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    model_type VARCHAR(50),                -- e.g., 'GBM', 'XGBoost', 'StackedEnsemble'
    mojo_path TEXT NOT NULL,
    training_dataset_id VARCHAR(255),      -- Lineage tracking
    metrics JSONB,                         -- {"auc": 0.92, "f1": 0.88, ...}
    hyperparameters JSONB,                 -- Training config
    feature_importance JSONB,              -- Feature weights
    training_duration_secs FLOAT,
    state VARCHAR(20) DEFAULT 'staging',   -- 'staging', 'production', 'archived'
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active 
    ON model_versions (is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_model_versions_state 
    ON model_versions (state, created_at DESC);

-- =============================================================================
-- Drift Events - Model Monitoring History
-- =============================================================================
-- SCN-01-02: Records PSI scores and triggered actions
-- =============================================================================

CREATE TABLE IF NOT EXISTS drift_events (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) REFERENCES model_versions(version),
    drift_scores JSONB NOT NULL,          -- {"feature_a": 0.15, "feature_b": 0.25}
    drifted_features TEXT[],               -- Features exceeding threshold
    max_psi FLOAT,
    mean_psi FLOAT,
    threshold FLOAT DEFAULT 0.2,
    action_taken VARCHAR(50),              -- 'retrain_triggered', 'alert_sent', 'none'
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drift_events_time 
    ON drift_events (detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_drift_events_version 
    ON drift_events (model_version, detected_at DESC);

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Function: Get latest feature vector for an entity
CREATE OR REPLACE FUNCTION get_latest_features(p_entity_id VARCHAR)
RETURNS JSONB AS $$
BEGIN
    RETURN (
        SELECT feature_vector 
        FROM features 
        WHERE entity_id = p_entity_id 
        ORDER BY event_time DESC 
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Get features at a specific point in time (time-travel)
CREATE OR REPLACE FUNCTION get_features_at_time(
    p_entity_id VARCHAR, 
    p_as_of TIMESTAMPTZ
)
RETURNS JSONB AS $$
BEGIN
    RETURN (
        SELECT feature_vector 
        FROM features 
        WHERE entity_id = p_entity_id 
          AND event_time <= p_as_of
        ORDER BY event_time DESC 
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Get prediction statistics for drift detection
CREATE OR REPLACE FUNCTION get_prediction_stats(
    p_model_version VARCHAR,
    p_days_back INT DEFAULT 7
)
RETURNS TABLE (
    feature_name TEXT,
    mean_value FLOAT,
    std_value FLOAT,
    min_value FLOAT,
    max_value FLOAT,
    sample_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        key AS feature_name,
        AVG((value::TEXT)::FLOAT) AS mean_value,
        STDDEV((value::TEXT)::FLOAT) AS std_value,
        MIN((value::TEXT)::FLOAT) AS min_value,
        MAX((value::TEXT)::FLOAT) AS max_value,
        COUNT(*) AS sample_count
    FROM prediction_logs, 
         jsonb_each(features) 
    WHERE model_version = p_model_version
      AND created_at > NOW() - (p_days_back || ' days')::INTERVAL
      AND jsonb_typeof(value) = 'number'
    GROUP BY key;
END;
$$ LANGUAGE plpgsql;

-- Function: Activate a model version (atomic swap)
-- SCN-01-01: Used for zero-downtime model updates
CREATE OR REPLACE FUNCTION activate_model(p_target_version VARCHAR)
RETURNS VOID AS $$
BEGIN
    -- Deactivate all models
    UPDATE model_versions 
    SET is_active = FALSE, state = 'archived', archived_at = NOW()
    WHERE is_active = TRUE;
    
    -- Activate target model
    UPDATE model_versions 
    SET 
        is_active = TRUE, 
        state = 'production',
        activated_at = NOW()
    WHERE version = p_target_version;
    
    -- Log the activation
    RAISE NOTICE 'Model % activated at %', p_target_version, NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: Record drift event and determine action
CREATE OR REPLACE FUNCTION record_drift_event(
    p_model_version VARCHAR,
    p_drift_scores JSONB,
    p_threshold FLOAT DEFAULT 0.2
)
RETURNS VARCHAR AS $$
DECLARE
    v_max_psi FLOAT;
    v_mean_psi FLOAT;
    v_drifted_features TEXT[];
    v_action VARCHAR(50);
BEGIN
    -- Calculate PSI statistics
    SELECT 
        MAX((value::TEXT)::FLOAT),
        AVG((value::TEXT)::FLOAT),
        ARRAY_AGG(key)
    INTO v_max_psi, v_mean_psi, v_drifted_features
    FROM jsonb_each(p_drift_scores)
    WHERE (value::TEXT)::FLOAT > p_threshold;
    
    -- Determine action
    IF v_max_psi > p_threshold * 2 THEN
        v_action := 'retrain_triggered';
    ELSIF v_max_psi > p_threshold THEN
        v_action := 'alert_sent';
    ELSE
        v_action := 'none';
    END IF;
    
    -- Insert drift event
    INSERT INTO drift_events (
        model_version, drift_scores, drifted_features, 
        max_psi, mean_psi, threshold, action_taken
    ) VALUES (
        p_model_version, p_drift_scores, v_drifted_features,
        v_max_psi, v_mean_psi, p_threshold, v_action
    );
    
    RETURN v_action;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Partition Maintenance Job (run via pg_cron or external scheduler)
-- =============================================================================
-- Execute regularly: SELECT partman.run_maintenance();
-- =============================================================================
