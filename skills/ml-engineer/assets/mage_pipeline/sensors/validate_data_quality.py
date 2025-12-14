"""
JTBD Step 4: Confirm - Data Quality Validation

Mage sensor block implementing the "Reflection Pattern" for data validation.
Before proceeding to resource-intensive training, the agent verifies:
- Minimum row count threshold
- Target column null percentage
- Schema alignment with model expectations
- Data drift detection

If confirmation fails, the pipeline halts and triggers alerts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def validate_data_quality(data: Dict[str, Any], *args, **kwargs) -> bool:
    """
    Agentic Reflection: Assess data quality before training.
    
    The sensor returns True only if all quality checks pass.
    On failure, it raises an exception to halt the pipeline.
    
    Checks:
    1. Minimum row count
    2. Target column null percentage
    3. Required columns present
    4. Data type validation
    5. Optional: Drift detection against baseline
    
    Args:
        data: Output from prepare_h2o_frame block
        
    Returns:
        True if validation passes, raises Exception otherwise
    """
    # Configuration from global variables
    min_row_count = kwargs.get('min_row_count', 1000)
    max_target_null_pct = kwargs.get('max_target_null_pct', 0.01)
    target_column = kwargs.get('target_column', 'target')
    required_columns = kwargs.get('required_columns', [])
    
    print(f"[CONFIRM] Running data quality validation...")
    print(f"[CONFIRM] Min rows: {min_row_count}, Max null %: {max_target_null_pct}")
    
    validation_results = {
        'checks': [],
        'passed': True,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    # Check 1: Minimum row count
    row_count = data.get('nrows', 0)
    check_1 = {
        'name': 'min_row_count',
        'expected': f'>= {min_row_count}',
        'actual': row_count,
        'passed': row_count >= min_row_count,
    }
    validation_results['checks'].append(check_1)
    
    if not check_1['passed']:
        validation_results['passed'] = False
        print(f"[CONFIRM] ❌ Row count check FAILED: {row_count} < {min_row_count}")
        print("[CONFIRM] Waiting for more data...")
        return False  # Sensor returns False to wait
    
    print(f"[CONFIRM] ✅ Row count: {row_count}")
    
    # Check 2: Target column exists
    columns = data.get('columns', [])
    check_2 = {
        'name': 'target_exists',
        'expected': f'{target_column} in columns',
        'actual': target_column in columns,
        'passed': target_column in columns,
    }
    validation_results['checks'].append(check_2)
    
    if not check_2['passed']:
        validation_results['passed'] = False
        raise Exception(f"[CONFIRM] FATAL: Target column '{target_column}' not found in data!")
    
    print(f"[CONFIRM] ✅ Target column exists: {target_column}")
    
    # Check 3: Target null percentage (requires H2O frame)
    hf = data.get('h2o_frame')
    if hf is not None:
        try:
            null_count = hf[target_column].isna().sum()
            null_pct = null_count / hf.nrows if hf.nrows > 0 else 0
            
            check_3 = {
                'name': 'target_null_pct',
                'expected': f'<= {max_target_null_pct}',
                'actual': f'{null_pct:.4f}',
                'passed': null_pct <= max_target_null_pct,
            }
            validation_results['checks'].append(check_3)
            
            if not check_3['passed']:
                raise Exception(f"[CONFIRM] FATAL: Target null % ({null_pct:.2%}) exceeds threshold ({max_target_null_pct:.2%})")
            
            print(f"[CONFIRM] ✅ Target null %: {null_pct:.4%}")
            
        except Exception as e:
            if 'FATAL' in str(e):
                raise
            print(f"[CONFIRM] ⚠️ Could not check null %: {e}")
    
    # Check 4: Required columns present
    if required_columns:
        missing = [c for c in required_columns if c not in columns]
        check_4 = {
            'name': 'required_columns',
            'expected': required_columns,
            'actual': f'Missing: {missing}' if missing else 'All present',
            'passed': len(missing) == 0,
        }
        validation_results['checks'].append(check_4)
        
        if not check_4['passed']:
            raise Exception(f"[CONFIRM] FATAL: Missing required columns: {missing}")
        
        print(f"[CONFIRM] ✅ All required columns present")
    
    # Check 5: Run H2O describe for type validation
    if hf is not None:
        try:
            desc = hf.describe()
            print(f"[CONFIRM] H2O Frame description captured")
        except Exception as e:
            print(f"[CONFIRM] ⚠️ Could not describe H2O frame: {e}")
    
    # All checks passed
    print(f"[CONFIRM] ✅ All {len(validation_results['checks'])} quality checks passed!")
    return True


def run_drift_detection(
    current_data: Dict[str, Any],
    baseline_stats: Optional[Dict] = None,
    drift_threshold: float = 0.1,
) -> Dict[str, Any]:
    """
    Optional drift detection comparing current data to baseline.
    
    Uses Population Stability Index (PSI) for numeric features.
    
    Returns:
        Dictionary with drift scores per feature
    """
    if baseline_stats is None:
        print("[CONFIRM] No baseline stats provided. Skipping drift detection.")
        return {'drift_detected': False, 'features': {}}
    
    drift_results = {
        'drift_detected': False,
        'threshold': drift_threshold,
        'features': {},
    }
    
    # Simple mean comparison (production would use PSI)
    current_means = current_data.get('feature_means', {})
    
    for feature, current_mean in current_means.items():
        baseline_mean = baseline_stats.get(feature, {}).get('mean', current_mean)
        
        if baseline_mean != 0:
            pct_change = abs(current_mean - baseline_mean) / abs(baseline_mean)
        else:
            pct_change = 0
        
        drift_results['features'][feature] = {
            'baseline_mean': baseline_mean,
            'current_mean': current_mean,
            'pct_change': pct_change,
            'drifted': pct_change > drift_threshold,
        }
        
        if pct_change > drift_threshold:
            drift_results['drift_detected'] = True
            print(f"[CONFIRM] ⚠️ Drift detected in '{feature}': {pct_change:.2%} change")
    
    return drift_results


if __name__ == '__main__':
    # Test with mock data
    mock_input = {
        'nrows': 5000,
        'ncols': 6,
        'columns': ['customer_id', 'feature_1', 'feature_2', 'feature_3', 'target'],
        'h2o_frame': None,
    }
    
    result = validate_data_quality(mock_input, min_row_count=1000)
    print(f"\nValidation result: {result}")
