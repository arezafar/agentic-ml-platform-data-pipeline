-- =============================================================================
-- Data Warehouse Foundation Schema (DDL)
-- =============================================================================
-- Phase 2, Task 2.2: Define Foundational Schema
--
-- This script creates the layered warehouse architecture:
--   1. raw_layer     - Landing zone for ingested data
--   2. staging_layer - Intermediate processing
--   3. analytical_layer - Curated data for analytics
--
-- Run against: postgres_warehouse (defined in io_config.yaml)
-- =============================================================================

-- =============================================================================
-- Create Schemas (Layers)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_layer;
COMMENT ON SCHEMA raw_layer IS 'Landing zone for raw ingested data';

CREATE SCHEMA IF NOT EXISTS staging_layer;
COMMENT ON SCHEMA staging_layer IS 'Intermediate processing and transformation';

CREATE SCHEMA IF NOT EXISTS analytical_layer;
COMMENT ON SCHEMA analytical_layer IS 'Curated, business-ready data';


-- =============================================================================
-- Raw Layer Tables
-- =============================================================================

-- Foundational Table: Incoming Metrics (based on H2O profiling)
CREATE TABLE IF NOT EXISTS raw_layer.incoming_metrics (
    id SERIAL PRIMARY KEY,
    sepal_len DOUBLE PRECISION,
    sepal_wid DOUBLE PRECISION,
    petal_len DOUBLE PRECISION,
    petal_wid DOUBLE PRECISION,
    class_label VARCHAR(50),  -- H2O identified as low-cardinality factor
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file VARCHAR(255),
    batch_id VARCHAR(100)
);

COMMENT ON TABLE raw_layer.incoming_metrics IS 
    'Raw iris metrics - schema designed from H2O profiling recommendations';

-- Index on frequently filtered columns (H2O identified high repetition)
CREATE INDEX IF NOT EXISTS idx_class_label 
    ON raw_layer.incoming_metrics(class_label);

CREATE INDEX IF NOT EXISTS idx_ingested_at 
    ON raw_layer.incoming_metrics(ingested_at);


-- Generic raw data landing table (JSONB for schema flexibility)
CREATE TABLE IF NOT EXISTS raw_layer.raw_events (
    event_id SERIAL PRIMARY KEY,
    source_system VARCHAR(100) NOT NULL,
    event_type VARCHAR(100),
    event_data JSONB NOT NULL,
    event_timestamp TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    batch_id VARCHAR(100)
);

COMMENT ON TABLE raw_layer.raw_events IS 
    'Generic raw event landing table with JSONB for schema-flexible ingestion';

CREATE INDEX IF NOT EXISTS idx_raw_events_source 
    ON raw_layer.raw_events(source_system, event_type);

CREATE INDEX IF NOT EXISTS idx_raw_events_timestamp 
    ON raw_layer.raw_events(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_events_data_gin 
    ON raw_layer.raw_events USING gin(event_data);


-- =============================================================================
-- Staging Layer Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS staging_layer.cleaned_metrics (
    id INTEGER PRIMARY KEY,
    sepal_length DOUBLE PRECISION NOT NULL,
    sepal_width DOUBLE PRECISION NOT NULL,
    petal_length DOUBLE PRECISION NOT NULL,
    petal_width DOUBLE PRECISION NOT NULL,
    species VARCHAR(50) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score FLOAT
);

COMMENT ON TABLE staging_layer.cleaned_metrics IS 
    'Cleaned and validated metrics ready for analytics';


-- =============================================================================
-- Analytical Layer Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytical_layer.species_summary (
    species VARCHAR(50) PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    avg_sepal_length DOUBLE PRECISION,
    avg_sepal_width DOUBLE PRECISION,
    avg_petal_length DOUBLE PRECISION,
    avg_petal_width DOUBLE PRECISION,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE analytical_layer.species_summary IS 
    'Aggregated species statistics for reporting';


-- =============================================================================
-- Audit & Metadata Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw_layer.pipeline_runs (
    run_id VARCHAR(100) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'failed')),
    rows_processed INTEGER,
    error_message TEXT
);

COMMENT ON TABLE raw_layer.pipeline_runs IS 
    'Track pipeline execution history for lineage';


-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Function to get latest batch ID for a source
CREATE OR REPLACE FUNCTION raw_layer.get_latest_batch(p_source VARCHAR)
RETURNS VARCHAR AS $$
    SELECT batch_id 
    FROM raw_layer.raw_events 
    WHERE source_system = p_source 
    ORDER BY ingested_at DESC 
    LIMIT 1;
$$ LANGUAGE SQL STABLE;
