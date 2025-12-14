"""
H2O Data Profiler - Schema Inference

Mage data loader that uses H2O to profile raw data and generate
schema recommendations for the data warehouse.

Phase 2, Task 2.1: Ingest & Profile Sample Data

The profiler analyzes:
- Data types (numeric, categorical, string)
- Cardinality (for ENUM vs VARCHAR decisions)
- Null percentages
- Statistical distributions

Output: Dictionary of column recommendations for DDL generation
"""

from typing import Any, Dict, Optional
import json


def load_data(*args, **kwargs) -> Dict[str, Any]:
    """
    Profile raw data using H2O and return schema recommendations.
    
    Args:
        file_path: Path to data file (CSV, Parquet, etc.)
        
    Returns:
        Dictionary with column recommendations for DDL
    """
    from os import environ
    
    # Configuration
    file_path = kwargs.get('file_path', 
        'https://s3.amazonaws.com/h2o-public-test-data/smalldata/iris/iris_wheader.csv')
    h2o_url = environ.get('H2O_URL', 'http://h2o:54321')
    
    try:
        import h2o
        
        # Initialize connection to the H2O container
        h2o.init(url=h2o_url)
        
        # Load raw data
        print(f"Loading data from: {file_path}")
        df_h2o = h2o.import_file(file_path)
        
        # Get summary statistics
        summary = df_h2o.describe()
        types = df_h2o.types
        
        # Generate schema recommendations
        recommendations = {}
        column_stats = {}
        
        for col in df_h2o.columns:
            col_type = types.get(col, 'unknown')
            stats = {
                'h2o_type': col_type,
                'null_count': int(df_h2o[col].isna().sum().as_data_frame().iloc[0, 0]),
                'row_count': df_h2o.nrows,
            }
            
            if df_h2o[col].isfactor():
                # Categorical column
                cardinality = df_h2o[col].nlevels()[0]
                stats['cardinality'] = cardinality
                
                if cardinality < 10:
                    recommendations[col] = {
                        'sql_type': 'VARCHAR(50)',
                        'recommendation': 'Low cardinality - consider ENUM or lookup table',
                        'index': True,
                    }
                elif cardinality < 50:
                    recommendations[col] = {
                        'sql_type': 'VARCHAR(100)',
                        'recommendation': 'Medium cardinality - consider lookup table for normalization',
                        'index': True,
                    }
                else:
                    recommendations[col] = {
                        'sql_type': 'VARCHAR(255)',
                        'recommendation': 'High cardinality - standard VARCHAR',
                        'index': False,
                    }
                    
            elif df_h2o[col].isnumeric():
                # Numeric column
                min_val = df_h2o[col].min()
                max_val = df_h2o[col].max()
                stats['min'] = min_val
                stats['max'] = max_val
                
                # Check if integer or float
                if df_h2o[col].isint():
                    if max_val < 2147483647 and min_val > -2147483648:
                        recommendations[col] = {
                            'sql_type': 'INTEGER',
                            'recommendation': 'Integer range fits in INT4',
                            'index': False,
                        }
                    else:
                        recommendations[col] = {
                            'sql_type': 'BIGINT',
                            'recommendation': 'Large integer - use BIGINT',
                            'index': False,
                        }
                else:
                    recommendations[col] = {
                        'sql_type': 'DOUBLE PRECISION',
                        'recommendation': 'Floating point - use DOUBLE PRECISION',
                        'index': False,
                    }
                    
            elif df_h2o[col].isstring():
                recommendations[col] = {
                    'sql_type': 'TEXT',
                    'recommendation': 'String column - use TEXT for flexibility',
                    'index': False,
                }
                
            else:
                recommendations[col] = {
                    'sql_type': 'TEXT',
                    'recommendation': f'Unknown type ({col_type}) - defaulting to TEXT',
                    'index': False,
                }
            
            column_stats[col] = stats
        
        # Calculate null percentage threshold
        null_threshold = 0.5
        nullable_columns = [
            col for col, stats in column_stats.items() 
            if stats['null_count'] / stats['row_count'] > null_threshold
        ]
        
        result = {
            'schema_recommendations': recommendations,
            'column_statistics': column_stats,
            'nullable_columns': nullable_columns,
            'total_rows': df_h2o.nrows,
            'total_columns': len(df_h2o.columns),
            'profiled_at': str(__import__('datetime').datetime.utcnow()),
        }
        
        print("\n=== Schema Recommendations ===")
        for col, rec in recommendations.items():
            print(f"  {col}: {rec['sql_type']} -- {rec['recommendation']}")
        
        return result
        
    except ImportError:
        print("⚠️  H2O not available. Returning mock profiling result.")
        return _mock_profiling_result()


def _mock_profiling_result() -> Dict[str, Any]:
    """Return mock profiling result when H2O is not available."""
    return {
        'schema_recommendations': {
            'sepal_length': {'sql_type': 'DOUBLE PRECISION', 'recommendation': 'Numeric', 'index': False},
            'sepal_width': {'sql_type': 'DOUBLE PRECISION', 'recommendation': 'Numeric', 'index': False},
            'petal_length': {'sql_type': 'DOUBLE PRECISION', 'recommendation': 'Numeric', 'index': False},
            'petal_width': {'sql_type': 'DOUBLE PRECISION', 'recommendation': 'Numeric', 'index': False},
            'class': {'sql_type': 'VARCHAR(50)', 'recommendation': 'Low cardinality factor', 'index': True},
        },
        'total_rows': 150,
        'total_columns': 5,
        'mock': True,
    }


# Mage decorator for standalone execution
if __name__ == '__main__':
    result = load_data()
    print(json.dumps(result, indent=2, default=str))
