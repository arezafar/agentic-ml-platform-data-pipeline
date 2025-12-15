"""
Drift Detection Sensor (Mage Block)
=============================================================================
SCN-01-02: Drift Detection Trigger Implementation

This sensor block monitors model performance and triggers retraining
when significant drift is detected using Population Stability Index (PSI).

Key Patterns:
- Calculates PSI between training baseline and recent predictions
- Triggers downstream retraining pipeline when drift > threshold
- Records drift events to PostgreSQL for historical analysis

Usage:
    1. Copy to your Mage project's sensors/ directory
    2. Configure as trigger for training pipeline
    3. Set schedule (e.g., hourly drift check)
=============================================================================
"""

import os
from typing import Any, Optional
import numpy as np
import pandas as pd

# Conditional imports for standalone testing
if __name__ != "__main__":
    from mage_ai.data_preparation.decorators import sensor
    from mage_ai.data_preparation.shared.secrets import get_secret_value
else:
    def sensor(func):
        return func
    def get_secret_value(key):
        return "test"


# Configuration
PSI_THRESHOLD = float(os.getenv("PSI_THRESHOLD", "0.2"))
LOOKBACK_DAYS = int(os.getenv("DRIFT_LOOKBACK_DAYS", "7"))
DATABASE_URL = os.getenv(
    "MAGE_DATABASE_CONNECTION_URL",
    "postgresql://mlops:mlops@postgres:5432/mlops"
)


def calculate_psi(
    baseline: np.ndarray,
    current: np.ndarray,
    bins: int = 10,
) -> float:
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures the shift in distribution between two populations.
    
    Interpretation:
    - PSI < 0.1: No significant change
    - 0.1 <= PSI < 0.2: Moderate change (monitor)
    - PSI >= 0.2: Significant change (action required)
    
    Args:
        baseline: Training distribution
        current: Recent prediction distribution
        bins: Number of bins for discretization
        
    Returns:
        PSI score (0 = identical, higher = more drift)
    """
    # Handle edge cases
    if len(baseline) == 0 or len(current) == 0:
        return 0.0
    
    # Create bins from baseline
    min_val = min(baseline.min(), current.min())
    max_val = max(baseline.max(), current.max())
    bin_edges = np.linspace(min_val, max_val, bins + 1)
    
    # Calculate proportions
    baseline_counts, _ = np.histogram(baseline, bins=bin_edges)
    current_counts, _ = np.histogram(current, bins=bin_edges)
    
    # Convert to proportions with smoothing to avoid division by zero
    baseline_props = (baseline_counts + 0.001) / (baseline_counts.sum() + 0.001 * bins)
    current_props = (current_counts + 0.001) / (current_counts.sum() + 0.001 * bins)
    
    # Calculate PSI
    psi = np.sum((current_props - baseline_props) * np.log(current_props / baseline_props))
    
    return float(psi)


def get_baseline_stats(
    model_version: str,
    connection_string: str,
) -> Optional[dict[str, dict[str, float]]]:
    """
    Retrieve baseline statistics from training metadata.
    
    Returns dict of {feature_name: {mean, std, min, max}}
    """
    import psycopg2
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Get baseline from model registry
        cursor.execute("""
            SELECT hyperparameters->>'baseline_stats'
            FROM model_versions
            WHERE version = %s AND is_active = TRUE
        """, (model_version,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            import json
            return json.loads(row[0])
        return None
        
    except Exception as e:
        print(f"Error retrieving baseline: {e}")
        return None


def get_recent_predictions(
    model_version: str,
    days_back: int,
    connection_string: str,
) -> pd.DataFrame:
    """
    Retrieve recent prediction features for drift analysis.
    """
    import psycopg2
    
    try:
        conn = psycopg2.connect(connection_string)
        
        query = """
            SELECT features
            FROM prediction_logs
            WHERE model_version = %s
              AND created_at > NOW() - INTERVAL '%s days'
            LIMIT 10000
        """
        
        df = pd.read_sql(query, conn, params=(model_version, days_back))
        conn.close()
        
        return df
        
    except Exception as e:
        print(f"Error retrieving predictions: {e}")
        return pd.DataFrame()


def record_drift_event(
    model_version: str,
    drift_scores: dict[str, float],
    threshold: float,
    action: str,
    connection_string: str,
) -> None:
    """
    Record drift detection event to database.
    """
    import psycopg2
    import json
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        drifted_features = [f for f, psi in drift_scores.items() if psi > threshold]
        max_psi = max(drift_scores.values()) if drift_scores else 0
        
        cursor.execute("""
            INSERT INTO drift_events 
            (model_version, drift_scores, drifted_features, max_psi, threshold, action_taken)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            model_version,
            json.dumps(drift_scores),
            drifted_features,
            max_psi,
            threshold,
            action,
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error recording drift event: {e}")


@sensor
def check_model_drift(*args, **kwargs) -> bool:
    """
    Sensor that detects feature drift and triggers retraining.
    
    SCN-01-02: Implements the drift detection scenario from the
    architectural specification.
    
    Returns:
        True if retraining should be triggered (drift detected)
        False if model is stable (no action needed)
    """
    # Get current model version
    model_version = kwargs.get("model_version", os.getenv("MODEL_VERSION", "latest"))
    threshold = kwargs.get("threshold", PSI_THRESHOLD)
    lookback_days = kwargs.get("lookback_days", LOOKBACK_DAYS)
    
    print(f"Checking drift for model {model_version}")
    print(f"PSI threshold: {threshold}, Lookback: {lookback_days} days")
    
    # Get baseline statistics
    baseline_stats = get_baseline_stats(model_version, DATABASE_URL)
    if not baseline_stats:
        print("No baseline stats found, skipping drift check")
        return False
    
    # Get recent predictions
    predictions_df = get_recent_predictions(model_version, lookback_days, DATABASE_URL)
    if predictions_df.empty:
        print("No recent predictions found, skipping drift check")
        return False
    
    # Extract features from JSONB
    import json
    features_list = []
    for _, row in predictions_df.iterrows():
        if isinstance(row['features'], str):
            features_list.append(json.loads(row['features']))
        else:
            features_list.append(row['features'])
    
    features_df = pd.DataFrame(features_list)
    
    # Calculate PSI for each numeric feature
    drift_scores = {}
    for feature in features_df.select_dtypes(include=[np.number]).columns:
        if feature in baseline_stats:
            baseline = baseline_stats[feature]
            # Reconstruct baseline distribution from stats
            baseline_mean = baseline.get('mean', 0)
            baseline_std = baseline.get('std', 1)
            baseline_samples = np.random.normal(baseline_mean, baseline_std, 1000)
            
            current_samples = features_df[feature].dropna().values
            
            if len(current_samples) > 10:
                psi = calculate_psi(baseline_samples, current_samples)
                drift_scores[feature] = psi
    
    # Analyze results
    if not drift_scores:
        print("No features to analyze for drift")
        return False
    
    max_psi = max(drift_scores.values())
    drifted_features = [f for f, psi in drift_scores.items() if psi > threshold]
    
    print(f"Drift analysis complete:")
    print(f"  Max PSI: {max_psi:.4f}")
    print(f"  Features with drift: {len(drifted_features)}/{len(drift_scores)}")
    
    # Determine action
    if max_psi > threshold * 2:
        action = "retrain_triggered"
        trigger_retrain = True
    elif max_psi > threshold:
        action = "alert_sent"
        trigger_retrain = True  # Still trigger but with warning
    else:
        action = "none"
        trigger_retrain = False
    
    # Record event
    record_drift_event(
        model_version=model_version,
        drift_scores=drift_scores,
        threshold=threshold,
        action=action,
        connection_string=DATABASE_URL,
    )
    
    if trigger_retrain:
        print(f"⚠️ DRIFT DETECTED - Action: {action}")
        print(f"Drifted features: {drifted_features}")
    else:
        print("✅ Model stable, no drift detected")
    
    return trigger_retrain


# Test harness
if __name__ == "__main__":
    # Test PSI calculation
    np.random.seed(42)
    baseline = np.random.normal(0, 1, 1000)
    
    # No drift
    current_same = np.random.normal(0, 1, 1000)
    psi_same = calculate_psi(baseline, current_same)
    print(f"PSI (same distribution): {psi_same:.4f}")
    
    # Moderate drift
    current_shifted = np.random.normal(0.5, 1, 1000)
    psi_shifted = calculate_psi(baseline, current_shifted)
    print(f"PSI (shifted mean): {psi_shifted:.4f}")
    
    # Significant drift
    current_different = np.random.normal(2, 2, 1000)
    psi_different = calculate_psi(baseline, current_different)
    print(f"PSI (different distribution): {psi_different:.4f}")
