"""
Data Exporter: Export to Warehouse

Mage data exporter block for the batch_load pipeline.
Writes transformed data to PostgreSQL warehouse.

Phase 3, Task 3.1: Build the ELT Pipeline
"""

from typing import Any, Dict, List


def export_data(data: List[Dict], *args, **kwargs) -> Dict[str, Any]:
    """
    Export data to PostgreSQL warehouse.
    
    Configuration (from io_config.yaml):
    - data_provider: postgres
    - data_provider_profile: dev
    - schema: raw_layer
    - table: incoming_metrics
    
    Args:
        data: List of transformed records
        
    Returns:
        Export statistics
    """
    from os import environ
    
    # Configuration
    target_schema = kwargs.get('schema', 'raw_layer')
    target_table = kwargs.get('table', 'incoming_metrics')
    batch_size = kwargs.get('batch_size', 1000)
    
    # Columns to export (must match table schema)
    columns = [
        'sepal_len', 'sepal_wid', 'petal_len', 'petal_wid',
        'class_label', 'ingested_at', 'source_file', 'batch_id'
    ]
    
    # Database connection
    db_config = {
        'host': environ.get('POSTGRES_HOST', 'postgres_warehouse'),
        'port': int(environ.get('POSTGRES_PORT', 5432)),
        'database': environ.get('POSTGRES_DBNAME', 'warehouse_db'),
        'user': environ.get('POSTGRES_USER', 'warehouse_admin'),
        'password': environ.get('POSTGRES_PASSWORD', 'warehouse_password'),
    }
    
    print(f"Exporting {len(data)} records to {target_schema}.{target_table}")
    
    try:
        import psycopg2
        from psycopg2.extras import execute_batch
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Build INSERT statement
        placeholders = ', '.join(['%s'] * len(columns))
        col_names = ', '.join(columns)
        
        insert_sql = f"""
            INSERT INTO {target_schema}.{target_table} ({col_names})
            VALUES ({placeholders})
        """
        
        # Prepare data as tuples
        rows = []
        for record in data:
            row = tuple(record.get(col) for col in columns)
            rows.append(row)
        
        # Batch insert
        execute_batch(cursor, insert_sql, rows, page_size=batch_size)
        conn.commit()
        
        print(f"✅ Exported {len(rows)} records to warehouse")
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'records_exported': len(rows),
            'target_table': f"{target_schema}.{target_table}",
        }
        
    except ImportError:
        print("⚠️  psycopg2 not available. Simulating export.")
        return _mock_export(data, target_schema, target_table)
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'records_attempted': len(data),
        }


def _mock_export(data: List[Dict], schema: str, table: str) -> Dict[str, Any]:
    """Simulate export when database is unavailable."""
    print(f"[MOCK] Would export {len(data)} records to {schema}.{table}")
    return {
        'status': 'mock',
        'records_exported': len(data),
        'target_table': f"{schema}.{table}",
    }


if __name__ == '__main__':
    # Test with sample data
    sample_data = [
        {
            'sepal_len': 5.1, 'sepal_wid': 3.5, 'petal_len': 1.4, 'petal_wid': 0.2,
            'class_label': 'Iris-setosa', 'ingested_at': '2024-01-01T00:00:00',
            'source_file': 'test.csv', 'batch_id': 'test_batch'
        }
    ]
    result = export_data(sample_data)
    print(result)
