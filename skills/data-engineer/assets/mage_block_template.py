"""
Mage OSS Block Templates

Individual block templates for different block types.
Use these as starting points for custom blocks.
"""

from typing import Any, Dict, List, Optional
from pandas import DataFrame


# =============================================================================
# DATA LOADER TEMPLATES
# =============================================================================

class DataLoaderTemplates:
    """Templates for data loader blocks."""
    
    @staticmethod
    def postgres_jsonb_loader(
        table_name: str,
        schema: str = 'raw_data_store',
        lookback_days: int = 1,
    ) -> str:
        """Generate a PostgreSQL JSONB data loader block."""
        return f'''
# @data_loader
def load_{table_name}(**kwargs) -> DataFrame:
    """Load data from {schema}.{table_name} JSONB store."""
    import asyncio
    import pandas as pd
    import asyncpg
    from os import environ
    
    async def fetch():
        conn = await asyncpg.connect(
            host=environ.get('DB_HOST', 'localhost'),
            port=int(environ.get('DB_PORT', 5432)),
            database=environ['DB_NAME'],
            user=environ['DB_USER'],
            password=environ['DB_PASSWORD'],
        )
        try:
            rows = await conn.fetch("""
                SELECT id, raw_payload::jsonb as data, ingested_at
                FROM {schema}.{table_name}
                WHERE ingested_at >= NOW() - INTERVAL '{lookback_days} days'
            """)
            return pd.DataFrame([dict(r) for r in rows])
        finally:
            await conn.close()
    
    return asyncio.run(fetch())
'''

    @staticmethod
    def api_loader(endpoint: str, auth_type: str = 'bearer') -> str:
        """Generate an API data loader block."""
        return f'''
# @data_loader
def load_from_api(**kwargs) -> DataFrame:
    """Load data from external API: {endpoint}"""
    import httpx
    import pandas as pd
    from os import environ
    
    headers = {{}}
    if '{auth_type}' == 'bearer':
        headers['Authorization'] = f"Bearer {{environ['API_TOKEN']}}"
    
    with httpx.Client() as client:
        response = client.get('{endpoint}', headers=headers)
        response.raise_for_status()
        data = response.json()
    
    return pd.DataFrame(data if isinstance(data, list) else [data])
'''


# =============================================================================
# TRANSFORMER TEMPLATES
# =============================================================================

class TransformerTemplates:
    """Templates for transformer blocks."""
    
    @staticmethod
    def flatten_jsonb() -> str:
        """Generate a JSONB flattening transformer."""
        return '''
# @transformer
def flatten_jsonb(df: DataFrame, **kwargs) -> DataFrame:
    """Flatten nested JSONB data column into separate columns."""
    import pandas as pd
    
    if 'data' not in df.columns:
        return df
    
    # Normalize JSON column
    json_df = pd.json_normalize(
        df['data'].apply(lambda x: x if isinstance(x, dict) else {})
    )
    
    # Merge with original dataframe (excluding 'data' column)
    result = pd.concat([
        df.drop('data', axis=1).reset_index(drop=True),
        json_df.reset_index(drop=True)
    ], axis=1)
    
    return result
'''

    @staticmethod
    def feature_engineering(features: List[str]) -> str:
        """Generate a feature engineering transformer."""
        feature_code = '\n    '.join([
            f"# TODO: Implement {f}" for f in features
        ])
        return f'''
# @transformer  
def engineer_features(df: DataFrame, **kwargs) -> DataFrame:
    """Engineer features for ML pipeline."""
    import pandas as pd
    
    # Feature implementations:
    {feature_code}
    
    # Add metadata
    df['feature_version'] = kwargs.get('feature_version', '1.0.0')
    df['computed_at'] = pd.Timestamp.now()
    
    return df
'''

    @staticmethod
    def data_quality_check() -> str:
        """Generate a data quality check transformer."""
        return '''
# @transformer
def check_data_quality(df: DataFrame, **kwargs) -> DataFrame:
    """Validate data quality and log issues."""
    import pandas as pd
    
    issues = []
    
    # Check for nulls in critical columns
    critical_cols = kwargs.get('critical_columns', [])
    for col in critical_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append(f"{col}: {null_count} null values")
    
    # Check for duplicates
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        issues.append(f"Found {duplicate_count} duplicate rows")
    
    # Log issues
    if issues:
        print(f"Data quality issues found: {issues}")
    else:
        print("Data quality check passed")
    
    # Add quality metadata
    df['dq_check_passed'] = len(issues) == 0
    df['dq_issues'] = str(issues) if issues else None
    
    return df
'''


# =============================================================================
# DATA EXPORTER TEMPLATES
# =============================================================================

class DataExporterTemplates:
    """Templates for data exporter blocks."""
    
    @staticmethod
    def postgres_feature_store(table_name: str, schema: str = 'feature_store') -> str:
        """Generate a PostgreSQL feature store exporter."""
        return f'''
# @data_exporter
def export_to_{table_name}(df: DataFrame, **kwargs) -> None:
    """Export features to {schema}.{table_name}"""
    import asyncio
    import asyncpg
    from os import environ
    
    async def export():
        conn = await asyncpg.connect(
            host=environ.get('DB_HOST', 'localhost'),
            port=int(environ.get('DB_PORT', 5432)),
            database=environ['DB_NAME'],
            user=environ['DB_USER'],
            password=environ['DB_PASSWORD'],
        )
        try:
            # Batch upsert
            records = df.to_dict('records')
            await conn.executemany("""
                INSERT INTO {schema}.{table_name} (entity_id, features, computed_at)
                VALUES ($1, $2::jsonb, $3)
                ON CONFLICT (entity_id) DO UPDATE 
                SET features = EXCLUDED.features, computed_at = EXCLUDED.computed_at
            """, [(r.get('id'), r, r.get('computed_at')) for r in records])
            
            print(f"Exported {{len(records)}} records")
        finally:
            await conn.close()
    
    asyncio.run(export())
'''


# =============================================================================
# SENSOR TEMPLATES  
# =============================================================================

class SensorTemplates:
    """Templates for sensor blocks (triggers)."""
    
    @staticmethod
    def cron_sensor(cron_expression: str) -> str:
        """Generate a cron-based sensor."""
        return f'''
# @sensor
def cron_trigger(**kwargs) -> bool:
    """Triggers pipeline on cron schedule: {cron_expression}"""
    # Mage handles cron scheduling internally
    # This sensor just validates conditions
    return True
'''

    @staticmethod
    def database_sensor(table_name: str, condition: str = 'new_rows') -> str:
        """Generate a database change sensor."""
        return f'''
# @sensor
def db_change_sensor(**kwargs) -> bool:
    """Triggers when {condition} detected in {table_name}"""
    import asyncio
    import asyncpg
    from os import environ
    
    async def check():
        conn = await asyncpg.connect(
            host=environ.get('DB_HOST', 'localhost'),
            database=environ['DB_NAME'],
            user=environ['DB_USER'],
            password=environ['DB_PASSWORD'],
        )
        try:
            # Check for new rows since last run
            last_run = kwargs.get('last_run_timestamp')
            if last_run:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE created_at > $1
                """, last_run)
                return count > 0
            return True
        finally:
            await conn.close()
    
    return asyncio.run(check())
'''


# =============================================================================
# BLOCK GENERATOR
# =============================================================================

def generate_block(
    block_type: str,
    template_name: str,
    **kwargs
) -> str:
    """Generate a block from a template.
    
    Args:
        block_type: Type of block (data_loader, transformer, data_exporter, sensor)
        template_name: Name of the template to use
        **kwargs: Template-specific parameters
        
    Returns:
        Generated block code as a string
    """
    templates = {
        'data_loader': DataLoaderTemplates,
        'transformer': TransformerTemplates,
        'data_exporter': DataExporterTemplates,
        'sensor': SensorTemplates,
    }
    
    template_class = templates.get(block_type)
    if not template_class:
        raise ValueError(f"Unknown block type: {block_type}")
    
    template_func = getattr(template_class, template_name, None)
    if not template_func:
        raise ValueError(f"Unknown template: {template_name}")
    
    return template_func(**kwargs)
