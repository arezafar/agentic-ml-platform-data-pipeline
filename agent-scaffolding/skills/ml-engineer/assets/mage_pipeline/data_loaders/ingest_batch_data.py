"""
Job 1: Batch Data Ingestion Pipeline

Mage Batch Pipeline for ETL operations. Implements data_loader blocks
to fetch raw data from multiple sources and transformer blocks to 
clean/prepare data before H2O conversion.

Success Criteria:
- Raw data loaded into Pandas/Polars DataFrame
- Ready for H2O conversion in downstream blocks
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import json


def ingest_batch_data(*args, **kwargs) -> Dict[str, Any]:
    """
    Universal batch data ingestion loader.
    
    Supports multiple data sources:
    - SQL databases (PostgreSQL, MySQL)
    - REST APIs
    - File formats (Parquet, CSV, JSON)
    - Cloud storage (S3, GCS)
    
    Configuration via kwargs:
    - source_type: 'sql' | 'api' | 'parquet' | 's3'
    - connection_config: Source-specific configuration
    
    Returns:
        Dictionary with DataFrame and metadata
    """
    from os import environ
    
    source_type = kwargs.get('source_type', 'sql')
    
    print(f"[INGEST] Starting batch ingestion from: {source_type}")
    
    if source_type == 'sql':
        return _load_from_sql(kwargs)
    elif source_type == 'api':
        return _load_from_api(kwargs)
    elif source_type == 'parquet':
        return _load_from_parquet(kwargs)
    elif source_type == 's3':
        return _load_from_s3(kwargs)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")


def _load_from_sql(config: Dict) -> Dict[str, Any]:
    """Load data from SQL database."""
    from os import environ
    
    try:
        import pandas as pd
        import psycopg2
        
        conn_config = {
            'host': config.get('host', environ.get('POSTGRES_HOST', 'postgres')),
            'port': int(config.get('port', environ.get('POSTGRES_PORT', 5432))),
            'database': config.get('database', environ.get('POSTGRES_DBNAME', 'feature_store')),
            'user': config.get('user', environ.get('POSTGRES_USER', 'mage')),
            'password': config.get('password', environ.get('POSTGRES_PASSWORD', 'mage_secret')),
        }
        
        query = config.get('query', 'SELECT * FROM training_data LIMIT 10000')
        
        print(f"[INGEST.SQL] Executing query on {conn_config['host']}")
        
        conn = psycopg2.connect(**conn_config)
        df = pd.read_sql(query, conn)
        conn.close()
        
        print(f"[INGEST.SQL] ✅ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        return {
            'dataframe': df,
            'source_type': 'sql',
            'row_count': len(df),
            'columns': list(df.columns),
            'ingested_at': datetime.utcnow().isoformat(),
        }
        
    except ImportError as e:
        print(f"[INGEST.SQL] ⚠️ Missing dependency: {e}")
        return _mock_data()


def _load_from_api(config: Dict) -> Dict[str, Any]:
    """Load data from REST API."""
    try:
        import pandas as pd
        import requests
        
        url = config.get('url')
        headers = config.get('headers', {})
        params = config.get('params', {})
        
        print(f"[INGEST.API] Fetching from: {url}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle nested JSON structures
        if isinstance(data, dict) and 'data' in data:
            data = data['data']
        
        df = pd.DataFrame(data)
        
        print(f"[INGEST.API] ✅ Loaded {len(df)} rows")
        
        return {
            'dataframe': df,
            'source_type': 'api',
            'row_count': len(df),
            'columns': list(df.columns),
            'ingested_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        print(f"[INGEST.API] ❌ Failed: {e}")
        return _mock_data()


def _load_from_parquet(config: Dict) -> Dict[str, Any]:
    """Load data from Parquet file."""
    try:
        import pandas as pd
        
        path = config.get('path')
        
        print(f"[INGEST.PARQUET] Loading from: {path}")
        
        df = pd.read_parquet(path)
        
        print(f"[INGEST.PARQUET] ✅ Loaded {len(df)} rows")
        
        return {
            'dataframe': df,
            'source_type': 'parquet',
            'row_count': len(df),
            'columns': list(df.columns),
            'source_path': path,
            'ingested_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        print(f"[INGEST.PARQUET] ❌ Failed: {e}")
        return _mock_data()


def _load_from_s3(config: Dict) -> Dict[str, Any]:
    """Load data from S3."""
    try:
        import pandas as pd
        import boto3
        from io import BytesIO
        
        bucket = config.get('bucket')
        key = config.get('key')
        
        print(f"[INGEST.S3] Loading from: s3://{bucket}/{key}")
        
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        
        if key.endswith('.parquet'):
            df = pd.read_parquet(BytesIO(obj['Body'].read()))
        else:
            df = pd.read_csv(BytesIO(obj['Body'].read()))
        
        print(f"[INGEST.S3] ✅ Loaded {len(df)} rows")
        
        return {
            'dataframe': df,
            'source_type': 's3',
            'row_count': len(df),
            'columns': list(df.columns),
            's3_path': f"s3://{bucket}/{key}",
            'ingested_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        print(f"[INGEST.S3] ❌ Failed: {e}")
        return _mock_data()


def _mock_data() -> Dict[str, Any]:
    """Return mock data for testing."""
    import random
    
    n_rows = 5000
    data = []
    
    for i in range(n_rows):
        data.append({
            'id': i,
            'feature_1': random.gauss(0, 1),
            'feature_2': random.gauss(5, 2),
            'feature_cat': random.choice(['A', 'B', 'C']),
            'target': random.choice([0, 1]),
        })
    
    return {
        'dataframe': data,
        'source_type': 'mock',
        'row_count': n_rows,
        'columns': ['id', 'feature_1', 'feature_2', 'feature_cat', 'target'],
        'mock': True,
    }


if __name__ == '__main__':
    result = ingest_batch_data(source_type='mock')
    print(json.dumps({k: v for k, v in result.items() if k != 'dataframe'}, indent=2))
