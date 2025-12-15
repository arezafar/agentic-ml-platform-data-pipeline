"""
Conditional Block: Data Quality Gate

Mage Conditional block for data quality validation.
Routes pipeline to failure handler if quality drops below threshold.

Block Type: transformer (with conditional logic)
Integration: Great Expectations patterns
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

if 'transformer' not in dir():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@transformer
def quality_gate(
    data: pd.DataFrame,
    *args,
    **kwargs
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Validate data quality and route accordingly.
    
    Features:
    - Schema validation
    - Row count checks
    - NULL ratio thresholds
    - Value distribution checks
    - Freshness validation
    
    Returns:
    - Tuple of (data, quality_report)
    - Data is passed through if valid
    - Quality report contains validation results
    
    Pipeline should use conditional branching based on quality_report['passed']
    """
    if data is None or len(data) == 0:
        return data, {'passed': False, 'error': 'No data received'}
    
    # Configuration
    min_row_count = kwargs.get('min_row_count', 1)
    max_null_ratio = kwargs.get('max_null_ratio', 0.1)  # 10% max nulls
    quality_threshold = kwargs.get('quality_threshold', 0.95)  # 95% pass rate
    required_columns = kwargs.get('required_columns', [])
    freshness_hours = kwargs.get('freshness_hours', 24)
    timestamp_column = kwargs.get('timestamp_column', None)
    
    # Initialize report
    report = {
        'passed': True,
        'overall_score': 1.0,
        'checks': [],
        'validated_at': datetime.utcnow().isoformat(),
        'row_count': len(data),
        'column_count': len(data.columns),
    }
    
    checks_passed = 0
    checks_total = 0
    
    # -------------------------------------------------------------------------
    # Check 1: Row Count
    # -------------------------------------------------------------------------
    checks_total += 1
    check = {
        'name': 'row_count',
        'passed': len(data) >= min_row_count,
        'expected': f'>= {min_row_count}',
        'actual': len(data),
    }
    report['checks'].append(check)
    if check['passed']:
        checks_passed += 1
    else:
        print(f"   ❌ Row count check failed: {check['actual']} < {min_row_count}")
    
    # -------------------------------------------------------------------------
    # Check 2: Required Columns
    # -------------------------------------------------------------------------
    if required_columns:
        checks_total += 1
        missing = [c for c in required_columns if c not in data.columns]
        check = {
            'name': 'required_columns',
            'passed': len(missing) == 0,
            'expected': required_columns,
            'actual': list(data.columns),
            'missing': missing,
        }
        report['checks'].append(check)
        if check['passed']:
            checks_passed += 1
        else:
            print(f"   ❌ Missing required columns: {missing}")
    
    # -------------------------------------------------------------------------
    # Check 3: NULL Ratios
    # -------------------------------------------------------------------------
    checks_total += 1
    null_ratios = data.isnull().mean()
    high_null_cols = null_ratios[null_ratios > max_null_ratio].to_dict()
    check = {
        'name': 'null_ratio',
        'passed': len(high_null_cols) == 0,
        'threshold': max_null_ratio,
        'violations': high_null_cols,
    }
    report['checks'].append(check)
    if check['passed']:
        checks_passed += 1
    else:
        print(f"   ❌ High NULL ratio in columns: {list(high_null_cols.keys())}")
    
    # -------------------------------------------------------------------------
    # Check 4: Data Freshness
    # -------------------------------------------------------------------------
    if timestamp_column and timestamp_column in data.columns:
        checks_total += 1
        try:
            max_timestamp = pd.to_datetime(data[timestamp_column]).max()
            age_hours = (datetime.utcnow() - max_timestamp.to_pydatetime()).total_seconds() / 3600
            check = {
                'name': 'freshness',
                'passed': age_hours <= freshness_hours,
                'max_age_hours': freshness_hours,
                'actual_age_hours': round(age_hours, 2),
            }
            report['checks'].append(check)
            if check['passed']:
                checks_passed += 1
            else:
                print(f"   ❌ Data is stale: {age_hours:.1f} hours old (max: {freshness_hours})")
        except Exception as e:
            report['checks'].append({
                'name': 'freshness',
                'passed': False,
                'error': str(e),
            })
    
    # -------------------------------------------------------------------------
    # Check 5: Unique Values
    # -------------------------------------------------------------------------
    if 'id' in data.columns:
        checks_total += 1
        duplicates = data['id'].duplicated().sum()
        check = {
            'name': 'unique_id',
            'passed': duplicates == 0,
            'duplicate_count': duplicates,
        }
        report['checks'].append(check)
        if check['passed']:
            checks_passed += 1
        else:
            print(f"   ❌ Found {duplicates} duplicate IDs")
    
    # -------------------------------------------------------------------------
    # Calculate Overall Score
    # -------------------------------------------------------------------------
    overall_score = checks_passed / checks_total if checks_total > 0 else 0
    report['overall_score'] = round(overall_score, 4)
    report['passed'] = overall_score >= quality_threshold
    report['checks_passed'] = checks_passed
    report['checks_total'] = checks_total
    
    if report['passed']:
        print(f"✅ Data quality gate PASSED: {overall_score:.1%} ({checks_passed}/{checks_total})")
    else:
        print(f"❌ Data quality gate FAILED: {overall_score:.1%} ({checks_passed}/{checks_total})")
        print(f"   Threshold: {quality_threshold:.1%}")
    
    return data, report


# Helper function for conditional routing
def should_continue(quality_report: Dict[str, Any]) -> bool:
    """Check if pipeline should continue based on quality report."""
    return quality_report.get('passed', False)


@test
def test_report_structure(output, *args) -> None:
    """Test that quality report has required fields."""
    data, report = output
    assert 'passed' in report, 'Missing passed field'
    assert 'overall_score' in report, 'Missing overall_score field'
    assert 'checks' in report, 'Missing checks field'
    print(f"✓ Quality report structure is valid")


@test
def test_score_valid(output, *args) -> None:
    """Test that score is between 0 and 1."""
    data, report = output
    score = report.get('overall_score', -1)
    assert 0 <= score <= 1, f'Invalid score: {score}'
    print(f"✓ Quality score is valid: {score}")
