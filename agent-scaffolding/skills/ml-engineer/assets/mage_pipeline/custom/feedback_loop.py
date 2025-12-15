"""
JTBD Step 7: Modify - Feedback Loop & Retraining Trigger

Implements the self-correction capability of the agentic workflow.
If monitoring indicates sub-optimal results or environment changes,
the agent triggers modifications:
- Retry with different hyperparameters
- Expand/constrain algorithm set
- Trigger full retraining from drift detection
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def handle_feedback(evaluation: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Agentic Self-Correction: Respond to monitoring feedback.
    
    Based on the evaluation decision:
    - APPROVE: Pass through to Conclude step
    - REJECT_BELOW_THRESHOLD: Trigger retraining with modified params
    - REVIEW_REQUIRED: Queue for human review
    
    This block can also be triggered by external events:
    - Data drift detection
    - Scheduled retraining
    - API trigger from monitoring system
    
    Args:
        evaluation: Output from evaluate_leaderboard block
        
    Returns:
        Dictionary with action taken and modified configuration
    """
    decision = evaluation.get('decision', 'UNKNOWN')
    
    print(f"[MODIFY] Processing feedback: {decision}")
    
    feedback_response = {
        'decision_received': decision,
        'action_taken': None,
        'modified_params': None,
        'processed_at': datetime.utcnow().isoformat(),
    }
    
    if decision == 'APPROVE_FOR_DEPLOYMENT':
        # No modification needed - pass through to Conclude
        feedback_response['action_taken'] = 'PASS_TO_CONCLUDE'
        feedback_response['proceed_to_deployment'] = True
        print(f"[MODIFY] ✅ Approved. Proceeding to deployment.")
        
    elif decision == 'REJECT_BELOW_THRESHOLD':
        # Self-correction: modify training parameters and retry
        feedback_response['action_taken'] = 'TRIGGER_RETRAINING'
        feedback_response['proceed_to_deployment'] = False
        
        # Generate modified parameters
        original_max_models = kwargs.get('max_models', 20)
        original_max_runtime = kwargs.get('max_runtime_secs', 3600)
        original_exclude = kwargs.get('exclude_algos', [])
        
        feedback_response['modified_params'] = {
            'max_models': min(original_max_models * 2, 50),  # Increase search
            'max_runtime_secs': int(original_max_runtime * 1.5),  # More time
            'exclude_algos': [],  # Remove exclusions (try everything)
            'attempt': kwargs.get('attempt', 1) + 1,
        }
        
        print(f"[MODIFY] Modifying parameters for retry:")
        print(f"[MODIFY]   max_models: {original_max_models} -> {feedback_response['modified_params']['max_models']}")
        print(f"[MODIFY]   max_runtime: {original_max_runtime}s -> {feedback_response['modified_params']['max_runtime_secs']}s")
        
        # Check if max attempts exceeded
        max_attempts = kwargs.get('max_attempts', 3)
        if feedback_response['modified_params']['attempt'] > max_attempts:
            feedback_response['action_taken'] = 'ESCALATE_TO_HUMAN'
            feedback_response['message'] = f"Max attempts ({max_attempts}) exceeded. Human review required."
            print(f"[MODIFY] ⚠️ Max attempts exceeded. Escalating to human review.")
        
    elif decision == 'REVIEW_REQUIRED':
        feedback_response['action_taken'] = 'QUEUE_FOR_REVIEW'
        feedback_response['proceed_to_deployment'] = False
        print(f"[MODIFY] ⚠️ Queued for human review.")
        
    else:
        feedback_response['action_taken'] = 'UNKNOWN_DECISION'
        feedback_response['proceed_to_deployment'] = False
        print(f"[MODIFY] ⚠️ Unknown decision: {decision}")
    
    return feedback_response


def trigger_drift_retraining(*args, **kwargs) -> Dict[str, Any]:
    """
    External trigger for retraining based on drift detection.
    
    This function can be invoked via Mage API trigger when:
    - Monitoring system detects data drift
    - Scheduled retraining window arrives
    - Performance decay detected in production
    
    Returns:
        Dictionary with retraining trigger configuration
    """
    trigger_source = kwargs.get('trigger_source', 'manual')
    drift_features = kwargs.get('drift_features', [])
    
    print(f"[MODIFY] Drift retraining triggered by: {trigger_source}")
    
    retraining_config = {
        'trigger_source': trigger_source,
        'drift_features': drift_features,
        'require_full_refresh': True,
        'priority': 'high' if drift_features else 'normal',
        'triggered_at': datetime.utcnow().isoformat(),
    }
    
    # If specific features drifted, might want to re-engineer them
    if drift_features:
        print(f"[MODIFY] Drifted features: {drift_features}")
        retraining_config['feature_investigation_required'] = True
    
    return retraining_config


if __name__ == '__main__':
    # Test with approve decision
    mock_eval = {'decision': 'APPROVE_FOR_DEPLOYMENT'}
    result = handle_feedback(mock_eval)
    print(json.dumps(result, indent=2))
    
    # Test with reject decision
    mock_eval = {'decision': 'REJECT_BELOW_THRESHOLD'}
    result = handle_feedback(mock_eval, max_models=20, max_runtime_secs=3600)
    print(json.dumps(result, indent=2))
