/*
 * dbt Model Template
 * 
 * Standardized SQL transformation template for the Agentic ML Platform.
 * 
 * Features:
 * - CTE-based structure for readability
 * - Data quality tests
 * - Incremental materialization support
 * - Lineage documentation
 * 
 * Configuration (dbt_project.yml):
 *   models:
 *     your_project:
 *       +materialized: incremental
 *       +unique_key: id
 *       +on_schema_change: append_new_columns
 */

{{/*
  Model Configuration
  
  Materialization options:
  - table: Full refresh each run
  - incremental: Append/merge new data only
  - view: Virtual table (no storage)
  - ephemeral: Inline subquery
*/}}
{{
  config(
    materialized = 'incremental',
    unique_key = 'id',
    schema = 'feature_store',
    tags = ['daily', 'ml-features'],
    
    -- Incremental strategy
    incremental_strategy = 'merge',
    merge_exclude_columns = ['created_at'],
    
    -- Performance
    cluster_by = ['entity_type', 'computed_at'],
    
    -- Documentation
    description = '{{ model_description }}'
  )
}}

-- =============================================================================
-- Model: {{ model_name }}
-- Description: {{ model_description }}
-- Owner: {{ owner }}
-- Upstream: {{ upstream_models }}
-- Downstream: {{ downstream_models }}
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CTE 1: Source Data
-- Pull raw data from upstream source
-- -----------------------------------------------------------------------------
WITH source_data AS (
    SELECT
        id,
        entity_id,
        entity_type,
        raw_payload,
        ingested_at,
        -- Extract JSON fields
        raw_payload->>'field_1' AS field_1,
        (raw_payload->>'field_2')::numeric AS field_2,
        raw_payload->>'field_3' AS field_3
    FROM {{ source('raw_data_store', 'raw_events') }}
    
    {% if is_incremental() %}
    -- Only process new records in incremental runs
    WHERE ingested_at > (SELECT MAX(computed_at) FROM {{ this }})
    {% endif %}
),

-- -----------------------------------------------------------------------------
-- CTE 2: Data Cleaning
-- Handle nulls, type casting, and basic validation
-- -----------------------------------------------------------------------------
cleaned_data AS (
    SELECT
        id,
        entity_id,
        entity_type,
        -- Null handling with defaults
        COALESCE(field_1, 'unknown') AS field_1,
        COALESCE(field_2, 0) AS field_2,
        NULLIF(TRIM(field_3), '') AS field_3,
        ingested_at,
        
        -- Data quality flags
        CASE 
            WHEN field_1 IS NULL THEN TRUE 
            ELSE FALSE 
        END AS has_missing_field_1
        
    FROM source_data
    -- Filter out invalid records
    WHERE entity_id IS NOT NULL
),

-- -----------------------------------------------------------------------------
-- CTE 3: Feature Engineering
-- Compute derived features for ML models
-- -----------------------------------------------------------------------------
feature_engineering AS (
    SELECT
        id,
        entity_id,
        entity_type,
        field_1,
        field_2,
        field_3,
        ingested_at,
        
        -- Aggregations
        SUM(field_2) OVER (
            PARTITION BY entity_id 
            ORDER BY ingested_at 
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS field_2_rolling_30d,
        
        -- Ratios
        CASE 
            WHEN field_2 > 0 
            THEN field_2 / NULLIF(
                AVG(field_2) OVER (PARTITION BY entity_type), 
                0
            )
            ELSE 0 
        END AS field_2_vs_avg,
        
        -- Time-based features
        EXTRACT(DOW FROM ingested_at) AS day_of_week,
        EXTRACT(HOUR FROM ingested_at) AS hour_of_day,
        
        -- Lag features
        LAG(field_2, 1) OVER (
            PARTITION BY entity_id 
            ORDER BY ingested_at
        ) AS field_2_lag_1,
        
        LAG(field_2, 7) OVER (
            PARTITION BY entity_id 
            ORDER BY ingested_at
        ) AS field_2_lag_7
        
    FROM cleaned_data
),

-- -----------------------------------------------------------------------------
-- CTE 4: Final Transformation
-- Assemble final feature set with metadata
-- -----------------------------------------------------------------------------
final AS (
    SELECT
        -- Primary key
        {{ dbt_utils.generate_surrogate_key(['entity_id', 'ingested_at']) }} AS id,
        
        -- Entity reference
        entity_id,
        entity_type,
        
        -- Features (as JSONB for flexibility)
        jsonb_build_object(
            'field_1', field_1,
            'field_2', field_2,
            'field_2_rolling_30d', field_2_rolling_30d,
            'field_2_vs_avg', ROUND(field_2_vs_avg::numeric, 4),
            'day_of_week', day_of_week,
            'hour_of_day', hour_of_day,
            'field_2_lag_1', field_2_lag_1,
            'field_2_lag_7', field_2_lag_7
        ) AS features,
        
        -- Metadata
        '{{ var("feature_version", "1.0.0") }}' AS feature_version,
        'dbt_{{ model_name }}' AS source_model,
        ingested_at AS computed_at,
        ingested_at AS valid_from,
        NULL::timestamptz AS valid_to,
        
        -- Audit
        CURRENT_TIMESTAMP AS created_at
        
    FROM feature_engineering
)

-- Output
SELECT * FROM final

/*
 * Testing (schema.yml):
 * 
 * models:
 *   - name: {{ model_name }}
 *     description: "{{ model_description }}"
 *     columns:
 *       - name: id
 *         tests:
 *           - unique
 *           - not_null
 *       - name: entity_id
 *         tests:
 *           - not_null
 *           - relationships:
 *               to: ref('entities')
 *               field: id
 *       - name: features
 *         tests:
 *           - not_null
 *       - name: computed_at
 *         tests:
 *           - not_null
 *           - dbt_expectations.expect_column_values_to_be_recent:
 *               interval: 1
 *               interval_type: day
 */
