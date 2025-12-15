"""
Data Loader: PostgreSQL Source

Mage Data Loader block for fetching data from PostgreSQL database.
Implements incremental loading with watermark tracking.

Block Type: data_loader
Connection: PostgreSQL via asyncpg

Usage in pipeline:
    @data_loader
    def load_postgres_data(**kwargs):
        ...
"""

from os import path
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

if 'data_loader' not in dir():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_from_postgres(
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Load data from PostgreSQL using incremental extraction.
    
    Supports:
    - Full load (initial extraction)
    - Incremental load (delta extraction using watermark)
    - Custom SQL queries
    
    Configuration via pipeline variables:
    - table_name: Source table name
    - schema_name: PostgreSQL schema
    - watermark_column: Column for incremental tracking
    - batch_size: Number of records per batch
    """
    from mage_ai.io.config import ConfigFileLoader
    from mage_ai.io.postgres import Postgres
    
    # Load configuration
    config_path = path.join(path.dirname(__file__), '..', 'io_config.yaml')
    config_profile = kwargs.get('profile', 'default')
    config = ConfigFileLoader(config_path, config_profile)
    
    # Get pipeline variables
    table_name = kwargs.get('table_name', 'raw_events')
    schema_name = kwargs.get('schema_name', 'raw_data_store')
    watermark_column = kwargs.get('watermark_column', 'ingested_at')
    batch_size = kwargs.get('batch_size', 50000)
    extraction_mode = kwargs.get('extraction_mode', 'incremental')
    
    # Get execution context
    execution_date = kwargs.get('execution_date', datetime.utcnow())
    
    # Build query based on extraction mode
    if extraction_mode == 'full':
        query = f"""
            SELECT *
            FROM {schema_name}.{table_name}
            ORDER BY {watermark_column}
            LIMIT {batch_size}
        """
    else:
        # Incremental: Get last watermark from runtime variables
        last_watermark = kwargs.get(
            'last_watermark', 
            (execution_date - timedelta(days=1)).isoformat()
        )
        
        query = f"""
            SELECT *
            FROM {schema_name}.{table_name}
            WHERE {watermark_column} > '{last_watermark}'::timestamptz
            ORDER BY {watermark_column}
            LIMIT {batch_size}
        """
    
    # Execute query
    with Postgres.with_config(config) as loader:
        df = loader.load(query)
    
    # Log extraction metadata
    record_count = len(df)
    print(f"✅ Loaded {record_count} records from {schema_name}.{table_name}")
    
    if record_count > 0 and watermark_column in df.columns:
        max_watermark = df[watermark_column].max()
        print(f"   Max watermark: {max_watermark}")
        # Store for next run
        kwargs['runtime_storage'] = {'last_watermark': str(max_watermark)}
    
    return df


@test
def test_output(output: pd.DataFrame, *args) -> None:
    """Test that output is valid."""
    assert output is not None, 'Output is undefined'
    assert isinstance(output, pd.DataFrame), 'Output must be a DataFrame'
    print(f"✓ Output validation passed: {len(output)} rows, {len(output.columns)} columns")


@test
def test_no_duplicates(output: pd.DataFrame, *args) -> None:
    """Test for duplicate primary keys."""
    if 'id' in output.columns:
        duplicates = output['id'].duplicated().sum()
        assert duplicates == 0, f'Found {duplicates} duplicate IDs'
        print(f"✓ No duplicate IDs found")
