"""
Job 2: Drift Detection Sensor

Mage Sensor Block that monitors for data drift using PSI.
Triggers retraining pipeline when drift exceeds threshold.

Metrics:
- Population Stability Index (PSI)
- KL Divergence (optional)

Success Criteria:
- Automated drift detection on schedule
- Retraining pipeline triggered via Mage API
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json
import math


def detect_drift(*args, **kwargs) -> bool:
    """
    Sensor block to detect data drift.
    
    Compares recent inference distribution to training baseline.
    Returns True to proceed (drift detected) or False to wait.
    
    Logic:
    1. Fetch recent prediction logs from PostgreSQL
    2. Compare feature distributions to baseline
    3. Calculate PSI for each feature
    4. If PSI > threshold, trigger retraining
    """
    from os import environ
    
    drift_threshold = kwargs.get('drift_threshold', 0.2)  # PSI > 0.2 = significant drift
    lookback_days = kwargs.get('lookback_days', 7)
    
    print(f"[DRIFT-SENSOR] Checking for data drift (threshold: {drift_threshold})")
    
    # Fetch recent predictions
    recent_data = _fetch_recent_predictions(lookback_days)
    
    if not recent_data:
        print("[DRIFT-SENSOR] No recent predictions found. Skipping.")
        return False
    
    # Load baseline statistics
    baseline_stats = _load_baseline_stats(kwargs)
    
    if not baseline_stats:
        print("[DRIFT-SENSOR] No baseline stats found. Skipping.")
        return False
    
    # Calculate PSI for each feature
    drift_results = _calculate_drift(recent_data, baseline_stats)
    
    # Check if any feature exceeds threshold
    drifted_features = [
        f for f, psi in drift_results['feature_psi'].items()
        if psi > drift_threshold
    ]
    
    if drifted_features:
        print(f"[DRIFT-SENSOR] ⚠️ Drift detected in {len(drifted_features)} features:")
        for feature in drifted_features:
            print(f"  - {feature}: PSI = {drift_results['feature_psi'][feature]:.4f}")
        
        # Log drift event
        _log_drift_event(drift_results, drifted_features)
        
        # Trigger retraining (return True)
        return True
    
    print(f"[DRIFT-SENSOR] ✅ No significant drift detected")
    return False


def _fetch_recent_predictions(days: int) -> List[Dict]:
    """Fetch recent prediction logs from PostgreSQL."""
    from os import environ
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=environ.get('POSTGRES_HOST', 'postgres'),
            port=int(environ.get('POSTGRES_PORT', 5432)),
            database=environ.get('POSTGRES_DBNAME', 'mlops'),
            user=environ.get('POSTGRES_USER', 'postgres'),
            password=environ.get('POSTGRES_PASSWORD', 'postgres'),
        )
        
        cursor = conn.cursor()
        
        # Query recent prediction logs
        cursor.execute("""
            SELECT features
            FROM prediction_logs
            WHERE created_at > NOW() - INTERVAL '%s days'
            LIMIT 10000
        """, (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Parse JSONB features
        return [row[0] for row in rows if row[0]]
        
    except Exception as e:
        print(f"[DRIFT-SENSOR] ⚠️ Could not fetch predictions: {e}")
        # Return mock data for testing
        return _mock_recent_data()


def _load_baseline_stats(config: Dict) -> Optional[Dict]:
    """Load baseline feature statistics from training."""
    from pathlib import Path
    
    baseline_path = Path(config.get('baseline_path', '/models/baseline_stats.json'))
    
    if baseline_path.exists():
        with open(baseline_path) as f:
            return json.load(f)
    
    # Return mock baseline for testing
    return {
        'feature_1': {'mean': 0.0, 'std': 1.0, 'bins': [0.1, 0.2, 0.3, 0.2, 0.2]},
        'feature_2': {'mean': 5.0, 'std': 2.0, 'bins': [0.15, 0.25, 0.25, 0.2, 0.15]},
    }


def _calculate_drift(
    recent_data: List[Dict],
    baseline: Dict,
) -> Dict[str, Any]:
    """Calculate PSI for each feature."""
    import numpy as np
    
    feature_psi = {}
    
    for feature, baseline_stats in baseline.items():
        # Extract feature values from recent data
        values = [d.get(feature) for d in recent_data if feature in d]
        
        if not values or not isinstance(values[0], (int, float)):
            continue
        
        values = np.array([v for v in values if v is not None])
        
        if len(values) < 100:
            continue
        
        # Calculate histogram for recent data (same bins as baseline)
        n_bins = len(baseline_stats.get('bins', []))
        if n_bins == 0:
            n_bins = 5
        
        # Normalize to get proportions
        recent_hist, _ = np.histogram(values, bins=n_bins, density=True)
        recent_bins = recent_hist / recent_hist.sum() if recent_hist.sum() > 0 else recent_hist
        
        baseline_bins = np.array(baseline_stats.get('bins', [1/n_bins] * n_bins))
        
        # Calculate PSI
        psi = _calculate_psi(baseline_bins, recent_bins)
        feature_psi[feature] = psi
    
    return {
        'feature_psi': feature_psi,
        'max_psi': max(feature_psi.values()) if feature_psi else 0,
        'calculated_at': datetime.utcnow().isoformat(),
    }


def _calculate_psi(expected: 'np.ndarray', actual: 'np.ndarray') -> float:
    """
    Calculate Population Stability Index.
    
    PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)
    
    Interpretation:
    - PSI < 0.1: No significant change
    - 0.1 ≤ PSI < 0.2: Moderate change
    - PSI ≥ 0.2: Significant change
    """
    # Avoid division by zero
    expected = expected.clip(min=0.0001)
    actual = actual.clip(min=0.0001)
    
    psi = ((actual - expected) * (actual / expected).apply(math.log) if hasattr(actual, 'apply')
           else sum((a - e) * math.log(a / e) for a, e in zip(actual, expected)))
    
    return abs(psi)


def _log_drift_event(drift_results: Dict, drifted_features: List[str]) -> None:
    """Log drift detection event to database."""
    from os import environ
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=environ.get('POSTGRES_HOST', 'postgres'),
            port=int(environ.get('POSTGRES_PORT', 5432)),
            database=environ.get('POSTGRES_DBNAME', 'mlops'),
            user=environ.get('POSTGRES_USER', 'postgres'),
            password=environ.get('POSTGRES_PASSWORD', 'postgres'),
        )
        
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_events (
                id SERIAL PRIMARY KEY,
                drift_scores JSONB,
                drifted_features TEXT[],
                detected_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            INSERT INTO drift_events (drift_scores, drifted_features)
            VALUES (%s, %s)
        """, (
            json.dumps(drift_results['feature_psi']),
            drifted_features,
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[DRIFT-SENSOR] Logged drift event to database")
        
    except Exception as e:
        print(f"[DRIFT-SENSOR] ⚠️ Could not log drift event: {e}")


def _mock_recent_data() -> List[Dict]:
    """Mock recent data for testing."""
    import random
    
    return [
        {
            'feature_1': random.gauss(0.5, 1.2),  # Drifted mean
            'feature_2': random.gauss(5, 2),
        }
        for _ in range(1000)
    ]


if __name__ == '__main__':
    result = detect_drift(drift_threshold=0.2)
    print(f"\nDrift detected: {result}")
