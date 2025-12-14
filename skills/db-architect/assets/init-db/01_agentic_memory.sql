-- =============================================================================
-- Agentic Memory Database Initialization
-- =============================================================================
-- Run on first PostgreSQL container startup
-- Creates extensions, schemas, and core tables for cognitive architecture
--
-- Prerequisites:
--   - PostgreSQL 15+
--   - pgvector extension available
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Schema: agent_memory
-- Core cognitive memory for AI agents
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS agent_memory;

-- Table: Semantic Knowledge Base (Long-term Memory)
CREATE TABLE IF NOT EXISTS agent_memory.knowledge_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_chunk TEXT NOT NULL,
    embedding VECTOR(1536),
    source_type VARCHAR(50),
    source_uri TEXT,
    author_id VARCHAR(100),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    attributes JSONB DEFAULT '{}'::jsonb,
    ingestion_run_id VARCHAR(255),
    is_consolidated BOOLEAN DEFAULT FALSE,
    ttl_expires_at TIMESTAMPTZ
);

COMMENT ON TABLE agent_memory.knowledge_items IS 
    'Semantic/Long-term Memory - Vectorized knowledge base for RAG retrieval';

-- HNSW Index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_hnsw 
    ON agent_memory.knowledge_items 
    USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_knowledge_source_type 
    ON agent_memory.knowledge_items (source_type);
    
CREATE INDEX IF NOT EXISTS idx_knowledge_creation_date 
    ON agent_memory.knowledge_items (creation_date);
    
CREATE INDEX IF NOT EXISTS idx_knowledge_attributes_gin 
    ON agent_memory.knowledge_items USING gin (attributes);


-- Table: Episodic Memory (Working/Short-term Memory)
CREATE TABLE IF NOT EXISTS agent_memory.episodes (
    episode_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    actor_role VARCHAR(20) NOT NULL 
        CHECK (actor_role IN ('user', 'agent', 'system', 'tool')),
    message_content TEXT,
    tool_call_details JSONB,
    tool_output JSONB,
    reasoning_trace TEXT,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_consolidated BOOLEAN DEFAULT FALSE,
    sentiment_score FLOAT
);

COMMENT ON TABLE agent_memory.episodes IS 
    'Episodic/Working Memory - Sequential interaction history and session state';

CREATE INDEX IF NOT EXISTS idx_episodes_session_sequence 
    ON agent_memory.episodes (session_id, sequence_number DESC);
    
CREATE INDEX IF NOT EXISTS idx_episodes_created_at 
    ON agent_memory.episodes (created_at);
    
CREATE INDEX IF NOT EXISTS idx_episodes_not_consolidated 
    ON agent_memory.episodes (is_consolidated) 
    WHERE is_consolidated = FALSE;


-- Table: Procedural Memory (Tool Usage Patterns)
CREATE TABLE IF NOT EXISTS agent_memory.tool_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(100) NOT NULL,
    tool_version VARCHAR(50),
    input_signature JSONB NOT NULL,
    output_summary TEXT,
    execution_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    context_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE agent_memory.tool_logs IS 
    'Procedural Memory - Tool usage patterns and success metrics for learning';

CREATE INDEX IF NOT EXISTS idx_tool_logs_name_success 
    ON agent_memory.tool_logs (tool_name, success);

CREATE INDEX IF NOT EXISTS idx_tool_logs_context_hnsw 
    ON agent_memory.tool_logs 
    USING hnsw (context_embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);


-- =============================================================================
-- Schema: h2o_intelligence
-- ML Model Registry and Capabilities Catalog
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS h2o_intelligence;

CREATE TABLE IF NOT EXISTS h2o_intelligence.model_registry (
    model_id VARCHAR(255) PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    problem_type VARCHAR(30) 
        CHECK (problem_type IN ('classification', 'regression', 'clustering', 'anomaly')),
    capabilities_description TEXT NOT NULL,
    required_features JSONB NOT NULL,
    target_column VARCHAR(100),
    validation_auc FLOAT,
    validation_rmse FLOAT,
    validation_logloss FLOAT,
    training_dataset VARCHAR(255),
    mojo_path TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

COMMENT ON TABLE h2o_intelligence.model_registry IS 
    'ML Model Catalog - Registry of H2O models available to agents';

CREATE INDEX IF NOT EXISTS idx_model_registry_active 
    ON h2o_intelligence.model_registry (is_active) 
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_model_registry_algorithm 
    ON h2o_intelligence.model_registry (algorithm);

CREATE INDEX IF NOT EXISTS idx_model_registry_problem_type 
    ON h2o_intelligence.model_registry (problem_type);


-- Model Metrics History (Drift Detection)
CREATE TABLE IF NOT EXISTS h2o_intelligence.model_metrics_history (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(255) NOT NULL 
        REFERENCES h2o_intelligence.model_registry(model_id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    dataset_name VARCHAR(255),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_model_time 
    ON h2o_intelligence.model_metrics_history (model_id, recorded_at);


-- =============================================================================
-- Schema: audit
-- Governance, Compliance, and Action Logging
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.agent_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID,
    agent_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL,
    resources_accessed JSONB,
    outcome VARCHAR(20) 
        CHECK (outcome IN ('success', 'failure', 'blocked', 'timeout')),
    risk_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET
);

COMMENT ON TABLE audit.agent_actions IS 
    'IMMUTABLE: Audit log for compliance - INSERT-only policies recommended';

CREATE INDEX IF NOT EXISTS idx_audit_agent_time 
    ON audit.agent_actions (agent_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_action_type 
    ON audit.agent_actions (action_type);

CREATE INDEX IF NOT EXISTS idx_audit_session 
    ON audit.agent_actions (session_id);


-- =============================================================================
-- Schema: system_control
-- Kill-switches and Global Agent Controls
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS system_control;

CREATE TABLE IF NOT EXISTS system_control.global_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

COMMENT ON TABLE system_control.global_settings IS 
    'Global control flags including kill-switch mechanism';

-- Seed critical control settings
INSERT INTO system_control.global_settings (setting_key, setting_value, description) 
VALUES 
    ('global_halt', '{"enabled": false, "reason": null}'::jsonb, 
        'Master kill-switch: stops all agent operations when enabled'),
    ('rate_limits', '{"max_queries_per_minute": 100, "max_tool_calls_per_session": 50, "max_model_inferences_per_hour": 1000}'::jsonb, 
        'Rate limiting configuration for agent operations'),
    ('allowed_models', '{"models": ["*"], "enforce": false}'::jsonb, 
        'Whitelist of models agents can use')
ON CONFLICT (setting_key) DO NOTHING;


-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Function: Check if system is halted (kill-switch)
CREATE OR REPLACE FUNCTION system_control.is_halted() 
RETURNS BOOLEAN AS $$
DECLARE
    halt_status BOOLEAN;
BEGIN
    SELECT (setting_value->>'enabled')::boolean INTO halt_status
    FROM system_control.global_settings
    WHERE setting_key = 'global_halt';
    
    RETURN COALESCE(halt_status, FALSE);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Semantic search in knowledge base
CREATE OR REPLACE FUNCTION agent_memory.semantic_search(
    query_embedding VECTOR(1536),
    limit_count INTEGER DEFAULT 10,
    source_filter VARCHAR DEFAULT NULL
)
RETURNS TABLE(
    item_id UUID,
    content_chunk TEXT,
    source_type VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ki.item_id,
        ki.content_chunk,
        ki.source_type,
        1 - (ki.embedding <=> query_embedding) AS similarity
    FROM agent_memory.knowledge_items ki
    WHERE 
        (source_filter IS NULL OR ki.source_type = source_filter)
        AND ki.embedding IS NOT NULL
    ORDER BY ki.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- Grant Permissions (adjust roles as needed)
-- =============================================================================
-- CREATE ROLE agent_read;
-- GRANT USAGE ON SCHEMA agent_memory, h2o_intelligence, system_control TO agent_read;
-- GRANT SELECT ON ALL TABLES IN SCHEMA agent_memory, h2o_intelligence, system_control TO agent_read;

-- CREATE ROLE agent_write;
-- GRANT agent_read TO agent_write;
-- GRANT INSERT, UPDATE ON agent_memory.episodes, agent_memory.tool_logs TO agent_write;
-- GRANT INSERT ON audit.agent_actions TO agent_write;

RAISE NOTICE 'Agentic Memory Database initialized successfully';
