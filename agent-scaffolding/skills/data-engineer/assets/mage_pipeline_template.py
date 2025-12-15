"""
Mage OSS Pipeline Template

This template provides the structure for a Mage pipeline that:
- Loads data from PostgreSQL JSONB raw data store
- Transforms data for the Feature Store
- Exports to the PostgreSQL Feature Store

Customize the blocks below for your specific use case.
"""

# Pipeline Configuration
PIPELINE_CONFIG = {
    'name': '{{ pipeline_name }}',
    'type': 'python',
    'description': '{{ pipeline_description }}',
    'tags': ['etl', 'feature-store'],
}


# =============================================================================
# DATA LOADER BLOCK
# =============================================================================
# @data_loader
def load_from_raw_store(**kwargs) -> 'DataFrame':
    """
    Load raw data from PostgreSQL JSONB store.
    
    This block connects to the Raw Data Store (Lakehouse) and extracts
    data using asyncpg for high-performance async operations.
    """
    import asyncio
    import pandas as pd
    
    # Configuration from environment or secrets
    config = {
        'host': '{{ db_host | default("localhost") }}',
        'port': {{ db_port | default(5432) }},
        'database': '{{ db_name }}',
        'user': '{{ db_user }}',
        'password': '{{ db_password }}',
    }
    
    query = """
    SELECT 
        id,
        raw_payload::jsonb as data,
        ingested_at
    FROM raw_data_store.{{ source_table }}
    WHERE ingested_at >= NOW() - INTERVAL '{{ lookback_interval | default("1 day") }}'
    """
    
    async def fetch_data():
        import asyncpg
        conn = await asyncpg.connect(**config)
        try:
            rows = await conn.fetch(query)
            return pd.DataFrame([dict(r) for r in rows])
        finally:
            await conn.close()
    
    return asyncio.run(fetch_data())


# =============================================================================
# TRANSFORMER BLOCK
# =============================================================================
# @transformer
def transform_to_features(df: 'DataFrame', **kwargs) -> 'DataFrame':
    """
    Transform raw data into features for the ML pipeline.
    
    This is a PURE function - no side effects, deterministic output.
    All feature engineering logic belongs here.
    """
    import pandas as pd
    
    # Extract nested JSONB fields
    if 'data' in df.columns:
        # Flatten JSONB column
        json_normalized = pd.json_normalize(df['data'].apply(
            lambda x: x if isinstance(x, dict) else {}
        ))
        df = pd.concat([df.drop('data', axis=1), json_normalized], axis=1)
    
    # Feature engineering examples:
    # 1. Date features
    if 'ingested_at' in df.columns:
        df['ingested_at'] = pd.to_datetime(df['ingested_at'])
        df['hour_of_day'] = df['ingested_at'].dt.hour
        df['day_of_week'] = df['ingested_at'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # 2. Numeric transformations
    # df['feature_scaled'] = (df['raw_value'] - df['raw_value'].mean()) / df['raw_value'].std()
    
    # 3. Categorical encoding
    # df['category_encoded'] = df['category'].astype('category').cat.codes
    
    # Add metadata
    df['feature_version'] = '{{ feature_version | default("1.0.0") }}'
    df['computed_at'] = pd.Timestamp.now()
    
    return df


# =============================================================================
# DATA EXPORTER BLOCK
# =============================================================================
# @data_exporter
def export_to_feature_store(df: 'DataFrame', **kwargs) -> None:
    """
    Export transformed features to PostgreSQL Feature Store.
    
    Uses UPSERT pattern with ON CONFLICT for idempotent writes.
    """
    import asyncio
    
    config = {
        'host': '{{ db_host | default("localhost") }}',
        'port': {{ db_port | default(5432) }},
        'database': '{{ db_name }}',
        'user': '{{ db_user }}',
        'password': '{{ db_password }}',
    }
    
    async def export_data():
        import asyncpg
        conn = await asyncpg.connect(**config)
        try:
            # Create table if not exists (with partitioning for time-series)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_store.{{ target_table }} (
                    id SERIAL PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    features JSONB NOT NULL,
                    feature_version TEXT NOT NULL,
                    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(entity_id, feature_version)
                ) PARTITION BY RANGE (computed_at)
            """)
            
            # Batch insert with UPSERT
            records = df.to_dict('records')
            await conn.executemany("""
                INSERT INTO feature_store.{{ target_table }} 
                    (entity_id, features, feature_version, computed_at)
                VALUES ($1, $2::jsonb, $3, $4)
                ON CONFLICT (entity_id, feature_version) 
                DO UPDATE SET 
                    features = EXCLUDED.features,
                    computed_at = EXCLUDED.computed_at
            """, [
                (r.get('id'), r, r.get('feature_version'), r.get('computed_at'))
                for r in records
            ])
            
            print(f"Exported {len(records)} records to feature store")
            
        finally:
            await conn.close()
    
    asyncio.run(export_data())


# =============================================================================
# PIPELINE METADATA (metadata.yaml equivalent)
# =============================================================================
PIPELINE_METADATA = {
    'name': PIPELINE_CONFIG['name'],
    'type': PIPELINE_CONFIG['type'],
    'blocks': [
        {
            'name': 'load_from_raw_store',
            'type': 'data_loader',
            'upstream_blocks': [],
            'downstream_blocks': ['transform_to_features'],
        },
        {
            'name': 'transform_to_features',
            'type': 'transformer',
            'upstream_blocks': ['load_from_raw_store'],
            'downstream_blocks': ['export_to_feature_store'],
        },
        {
            'name': 'export_to_feature_store',
            'type': 'data_exporter',
            'upstream_blocks': ['transform_to_features'],
            'downstream_blocks': [],
        },
    ],
}
