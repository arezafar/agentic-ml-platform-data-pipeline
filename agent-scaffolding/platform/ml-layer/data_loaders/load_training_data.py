"""
JTBD Step 2: Locate - Data Ingestion

Mage data loader that implements the "Tool Use" pattern for parametric
data retrieval. Fetches training data from upstream sources using
runtime variables for incremental processing.

Key Features:
- Dynamic SQL with execution_date parameter
- Incremental/backfill support
- Secure credential interpolation
- Zero-copy export to shared volume for H2O import
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def load_training_data(*args, **kwargs) -> Dict[str, Any]:
    """
    Agentic Tool Use: Fetch training data from Feature Store.
    
    The agent uses runtime variables to construct dynamic queries,
    enabling incremental processing without code changes.
    
    Configuration from kwargs:
    - execution_date: Date partition to load
    - training_table: Source table name
    - full_refresh: If True, load all data
    
    Returns:
        Dictionary with query results and metadata
    """
    from os import environ
    
    # Extract execution context
    execution_date = kwargs.get('execution_date', datetime.now().strftime('%Y-%m-%d'))
    training_table = kwargs.get('training_table', 'feature_store.training_features')
    full_refresh = kwargs.get('full_refresh', False)
    
    print(f"[LOCATE] Loading data for execution_date: {execution_date}")
    print(f"[LOCATE] Source table: {training_table}")
    
    # Construct parametric query
    if full_refresh:
        query = f"""
            SELECT *
            FROM {training_table}
            WHERE is_active = true
        """
    else:
        # Incremental: only load data for execution date
        query = f"""
            SELECT *
            FROM {training_table}
            WHERE created_date = '{execution_date}'
              AND is_active = true
        """
    
    # In Mage, this would use the postgres loader
    # from mage_ai.io.postgres import Postgres
    # with Postgres.with_config(config) as loader:
    #     df = loader.load(query)
    
    try:
        import psycopg2
        import pandas as pd
        
        # Get connection from environment
        conn_config = {
            'host': environ.get('POSTGRES_HOST', 'postgres'),
            'port': int(environ.get('POSTGRES_PORT', 5432)),
            'database': environ.get('POSTGRES_DBNAME', 'feature_store'),
            'user': environ.get('POSTGRES_USER', 'mage'),
            'password': environ.get('POSTGRES_PASSWORD', 'mage_secret'),
        }
        
        conn = psycopg2.connect(**conn_config)
        df = pd.read_sql(query, conn)
        conn.close()
        
        print(f"[LOCATE] ✅ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Export to shared volume for zero-copy H2O import
        data_path = environ.get('DATA_EXCHANGE_PATH', '/data/exchange')
        export_path = f"{data_path}/training_data_{execution_date.replace('-', '')}.csv"
        df.to_csv(export_path, index=False)
        print(f"[LOCATE] Exported to: {export_path}")
        
        return {
            'dataframe': df,
            'csv_path': export_path,
            'row_count': len(df),
            'columns': list(df.columns),
            'execution_date': execution_date,
            'query': query,
        }
        
    except ImportError:
        print("[LOCATE] ⚠️ Database not available. Returning mock data.")
        return _mock_training_data(execution_date)


def _mock_training_data(execution_date: str) -> Dict[str, Any]:
    """Return mock training data for testing."""
    import random
    
    n_rows = 5000
    mock_data = []
    
    for i in range(n_rows):
        mock_data.append({
            'customer_id': f'CUST_{i:06d}',
            'feature_1': random.gauss(0, 1),
            'feature_2': random.gauss(5, 2),
            'feature_3': random.choice(['A', 'B', 'C']),
            'feature_4': random.uniform(0, 100),
            'target': random.choice([0, 1]),
        })
    
    return {
        'dataframe': mock_data,
        'csv_path': f'/data/exchange/mock_training_{execution_date}.csv',
        'row_count': n_rows,
        'columns': ['customer_id', 'feature_1', 'feature_2', 'feature_3', 'feature_4', 'target'],
        'execution_date': execution_date,
        'mock': True,
    }


if __name__ == '__main__':
    result = load_training_data()
    print(json.dumps({k: v for k, v in result.items() if k != 'dataframe'}, indent=2))
