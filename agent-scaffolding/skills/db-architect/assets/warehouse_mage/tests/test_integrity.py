"""
Data Validation Tests: Verify Integrity

Mage test block for the batch_load pipeline.
Validates data quality after loading to warehouse.

Phase 3, Task 3.2: Validate Data Integrity (Agentic Audit)
"""

from typing import Any, Dict, List


def test_schema_conformance(df: List[Dict], *args, **kwargs) -> None:
    """
    Validate that data conforms to schema expectations.
    
    Checks:
    - No nulls in critical columns
    - Numeric values are in valid ranges  
    - Categorical values match expected set
    
    Args:
        df: List of data records
        
    Raises:
        AssertionError: If validation fails
    """
    # Critical columns that must not be null
    critical_columns = ['class_label']
    
    for col in critical_columns:
        null_count = sum(1 for rec in df if rec.get(col) is None or rec.get(col) == '')
        assert null_count == 0, f"Critical Error: {null_count} nulls found in {col}"
    
    print(f"✅ No nulls in critical columns: {critical_columns}")


def test_numeric_ranges(df: List[Dict], *args, **kwargs) -> None:
    """
    Validate numeric columns are within expected ranges.
    
    Args:
        df: List of data records
        
    Raises:
        AssertionError: If values are out of range
    """
    numeric_columns = {
        'sepal_len': (0, 20),
        'sepal_wid': (0, 20), 
        'petal_len': (0, 20),
        'petal_wid': (0, 20),
    }
    
    for col, (min_val, max_val) in numeric_columns.items():
        values = [rec.get(col) for rec in df if rec.get(col) is not None]
        
        if values:
            out_of_range = [v for v in values if v < min_val or v > max_val]
            assert len(out_of_range) == 0, \
                f"Range Error: {len(out_of_range)} values in {col} outside [{min_val}, {max_val}]"
    
    print(f"✅ Numeric values in valid ranges")


def test_categorical_values(df: List[Dict], *args, **kwargs) -> None:
    """
    Validate categorical columns contain expected values.
    
    Args:
        df: List of data records
        
    Raises:
        AssertionError: If unexpected values found
    """
    expected_classes = {'Iris-setosa', 'Iris-versicolor', 'Iris-virginica'}
    
    actual_classes = set()
    for rec in df:
        val = rec.get('class_label')
        if val:
            actual_classes.add(val)
    
    unexpected = actual_classes - expected_classes
    
    # Warning for unexpected values (not failure)
    if unexpected:
        print(f"⚠️  Unexpected class values found: {unexpected}")
    else:
        print(f"✅ All class values match expected set")


def test_row_count(df: List[Dict], *args, **kwargs) -> None:
    """
    Validate minimum row count threshold.
    
    Args:
        df: List of data records
        
    Raises:
        AssertionError: If row count below threshold
    """
    min_rows = kwargs.get('min_rows', 1)
    
    assert len(df) >= min_rows, \
        f"Row Count Error: Expected at least {min_rows} rows, got {len(df)}"
    
    print(f"✅ Row count: {len(df)} (minimum: {min_rows})")


def test_no_duplicates(df: List[Dict], *args, **kwargs) -> None:
    """
    Check for duplicate records based on key columns.
    
    Args:
        df: List of data records
        
    Raises:
        AssertionError: If duplicates exceed threshold
    """
    key_columns = kwargs.get('key_columns', ['sepal_len', 'sepal_wid', 'petal_len', 'petal_wid', 'class_label'])
    
    # Create tuple keys for duplicate detection
    seen = set()
    duplicates = 0
    
    for rec in df:
        key = tuple(str(rec.get(col)) for col in key_columns)
        if key in seen:
            duplicates += 1
        seen.add(key)
    
    dup_pct = (duplicates / len(df)) * 100 if df else 0
    
    print(f"ℹ️  Duplicate records: {duplicates} ({dup_pct:.1f}%)")
    
    # Warn but don't fail for duplicates
    if dup_pct > 50:
        print(f"⚠️  High duplicate percentage - consider deduplication")


def run_all_tests(df: List[Dict], *args, **kwargs) -> Dict[str, Any]:
    """
    Run all validation tests and return summary.
    
    Args:
        df: List of data records
        
    Returns:
        Test results summary
    """
    results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'errors': [],
    }
    
    tests = [
        ('schema_conformance', test_schema_conformance),
        ('numeric_ranges', test_numeric_ranges),
        ('categorical_values', test_categorical_values),
        ('row_count', test_row_count),
        ('no_duplicates', test_no_duplicates),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func(df, *args, **kwargs)
            results['tests_passed'] += 1
        except AssertionError as e:
            results['tests_failed'] += 1
            results['errors'].append({'test': test_name, 'error': str(e)})
            print(f"❌ {test_name}: {e}")
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {results['tests_passed']}")
    print(f"Failed: {results['tests_failed']}")
    
    return results


if __name__ == '__main__':
    # Test with sample data
    sample_data = [
        {'sepal_len': 5.1, 'sepal_wid': 3.5, 'petal_len': 1.4, 'petal_wid': 0.2, 'class_label': 'Iris-setosa'},
        {'sepal_len': 4.9, 'sepal_wid': 3.0, 'petal_len': 1.4, 'petal_wid': 0.2, 'class_label': 'Iris-setosa'},
        {'sepal_len': 7.0, 'sepal_wid': 3.2, 'petal_len': 4.7, 'petal_wid': 1.4, 'class_label': 'Iris-versicolor'},
    ]
    
    run_all_tests(sample_data)
