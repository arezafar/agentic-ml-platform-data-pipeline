"""
Transformer: Clean and Transform Columns

Mage transformer block for the batch_load pipeline.
Renames and transforms columns to match warehouse schema.

Phase 3, Task 3.1: Build the ELT Pipeline
"""

from typing import Any, Dict, List


def transform(data: List[Dict], *args, **kwargs) -> List[Dict]:
    """
    Transform source data to match warehouse schema.
    
    Transformations:
    - Rename columns to match target schema
    - Type coercion
    - Handle nulls and defaults
    - Add audit columns
    
    Args:
        data: List of source records
        
    Returns:
        List of transformed records ready for warehouse
    """
    from datetime import datetime
    
    # Column mapping (source -> target)
    column_map = kwargs.get('column_map', {
        'sepal_length': 'sepal_len',
        'sepal_width': 'sepal_wid',
        'petal_length': 'petal_len',
        'petal_width': 'petal_wid',
        'class': 'class_label',
    })
    
    # Numeric columns that need type coercion
    numeric_columns = ['sepal_len', 'sepal_wid', 'petal_len', 'petal_wid']
    
    transformed = []
    errors = []
    
    for idx, record in enumerate(data):
        try:
            new_record = {}
            
            # Apply column mapping
            for source_col, target_col in column_map.items():
                if source_col in record:
                    new_record[target_col] = record[source_col]
            
            # Copy unmapped columns
            for key, value in record.items():
                if key not in column_map and not key.startswith('_'):
                    new_record[key] = value
            
            # Type coercion for numeric columns
            for col in numeric_columns:
                if col in new_record:
                    try:
                        val = new_record[col]
                        if val is None or val == '' or val == 'N/A':
                            new_record[col] = None
                        else:
                            new_record[col] = float(val)
                    except (ValueError, TypeError):
                        new_record[col] = None
            
            # Add audit columns
            new_record['ingested_at'] = datetime.utcnow().isoformat()
            new_record['batch_id'] = record.get('_batch_id', 'unknown')
            new_record['source_file'] = record.get('_source_file', 'unknown')
            
            transformed.append(new_record)
            
        except Exception as e:
            errors.append({'row': idx, 'error': str(e), 'record': record})
    
    # Log transformation results
    print(f"✅ Transformed {len(transformed)} records")
    if errors:
        print(f"⚠️  {len(errors)} records had errors")
        for err in errors[:5]:  # Show first 5 errors
            print(f"   Row {err['row']}: {err['error']}")
    
    return transformed


def test_transform():
    """Test the transformer with sample data."""
    sample_data = [
        {'sepal_length': '5.1', 'sepal_width': '3.5', 'petal_length': '1.4', 
         'petal_width': '0.2', 'class': 'Iris-setosa', '_batch_id': 'test'},
        {'sepal_length': 'N/A', 'sepal_width': '3.0', 'petal_length': '1.4', 
         'petal_width': '0.2', 'class': 'Iris-setosa', '_batch_id': 'test'},
    ]
    
    result = transform(sample_data)
    print(f"Transformed {len(result)} records")
    for r in result:
        print(f"  {r}")


if __name__ == '__main__':
    test_transform()
