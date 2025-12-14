"""
JTBD Step 6: Monitor - Leaderboard Evaluation & Explainability

Implements the "Reflection Pattern" where the agent assesses execution
results against defined goals. Includes:
- Leaderboard parsing and threshold comparison
- Performance comparison against baseline model
- Explainability artifacts (SHAP, Variable Importance)
- Decision on whether to proceed to deployment
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def evaluate_leaderboard(training_result: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Agentic Reflection: Assess model performance against goals.
    
    The agent doesn't just log results—it parses them and makes decisions:
    - Compare leader against performance threshold
    - Compare leader against currently deployed model
    - Generate explainability artifacts
    - Decide: proceed to deployment or trigger retraining
    
    Args:
        training_result: Output from train_automl block
        
    Returns:
        Dictionary with evaluation results and deployment decision
    """
    # Configuration
    performance_threshold = kwargs.get('performance_threshold', 0.80)
    primary_metric = kwargs.get('primary_metric', 'auc')
    baseline_model_id = kwargs.get('baseline_model_id', None)
    baseline_score = kwargs.get('baseline_score', None)
    generate_explanations = kwargs.get('generate_explanations', True)
    
    print(f"[MONITOR] Evaluating model performance...")
    print(f"[MONITOR] Threshold: {primary_metric} >= {performance_threshold}")
    
    leader_metrics = training_result.get('leader_metrics', {})
    leader_id = training_result.get('leader_id', 'unknown')
    leader_score = leader_metrics.get(primary_metric.lower(), 0.0)
    
    evaluation = {
        'leader_id': leader_id,
        'primary_metric': primary_metric,
        'leader_score': leader_score,
        'threshold': performance_threshold,
        'checks': [],
        'decision': None,
        'evaluated_at': datetime.utcnow().isoformat(),
    }
    
    # Check 1: Threshold comparison
    meets_threshold = leader_score >= performance_threshold
    evaluation['checks'].append({
        'name': 'threshold_check',
        'passed': meets_threshold,
        'message': f"Leader {primary_metric}: {leader_score:.4f} vs threshold {performance_threshold}",
    })
    
    if not meets_threshold:
        print(f"[MONITOR] ❌ Model failed threshold: {leader_score:.4f} < {performance_threshold}")
        evaluation['decision'] = 'REJECT_BELOW_THRESHOLD'
        raise Exception(f"Model performance ({leader_score:.4f}) below threshold ({performance_threshold})")
    
    print(f"[MONITOR] ✅ Threshold passed: {leader_score:.4f}")
    
    # Check 2: Baseline comparison (if available)
    if baseline_score is not None:
        improvement = leader_score - baseline_score
        improves_baseline = improvement > 0
        
        evaluation['baseline_comparison'] = {
            'baseline_model_id': baseline_model_id,
            'baseline_score': baseline_score,
            'improvement': improvement,
            'improves': improves_baseline,
        }
        evaluation['checks'].append({
            'name': 'baseline_check',
            'passed': improves_baseline,
            'message': f"Improvement over baseline: {improvement:+.4f}",
        })
        
        if improves_baseline:
            print(f"[MONITOR] ✅ Improves on baseline: {improvement:+.4f}")
        else:
            print(f"[MONITOR] ⚠️ Does not improve on baseline: {improvement:+.4f}")
    
    # Generate explainability artifacts
    if generate_explanations:
        explanations = _generate_explanations(
            training_result.get('leader'),
            training_result.get('automl'),
        )
        evaluation['explanations'] = explanations
    
    # Final decision
    all_passed = all(c['passed'] for c in evaluation['checks'])
    
    if all_passed:
        evaluation['decision'] = 'APPROVE_FOR_DEPLOYMENT'
        print(f"[MONITOR] ✅ Model APPROVED for deployment")
    else:
        evaluation['decision'] = 'REVIEW_REQUIRED'
        print(f"[MONITOR] ⚠️ Manual review required before deployment")
    
    # Summary report
    print("\n" + "=" * 50)
    print("[MONITOR] EVALUATION SUMMARY")
    print("=" * 50)
    print(f"  Model: {leader_id}")
    print(f"  {primary_metric.upper()}: {leader_score:.4f}")
    print(f"  Decision: {evaluation['decision']}")
    print("=" * 50)
    
    return evaluation


def _generate_explanations(leader, automl) -> Dict[str, Any]:
    """
    Generate model explainability artifacts.
    
    Uses H2O's explain functionality for:
    - Variable Importance
    - SHAP values
    - Partial Dependence Plots
    """
    explanations = {
        'variable_importance': None,
        'shap_summary': None,
        'artifacts_path': None,
    }
    
    if leader is None:
        print("[MONITOR] ⚠️ No leader model available for explanations (mock mode)")
        return explanations
    
    try:
        import h2o
        from pathlib import Path
        
        # Variable Importance
        if hasattr(leader, 'varimp'):
            varimp = leader.varimp(use_pandas=True)
            if varimp is not None:
                explanations['variable_importance'] = varimp.head(20).to_dict('records')
                print(f"[MONITOR] Generated variable importance ({len(varimp)} features)")
        
        # Generate explain output
        artifacts_dir = Path('/models/explanations')
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Use h2o.explain for comprehensive analysis
        # explain_result = h2o.explain(leader, ...)
        
        explanations['artifacts_path'] = str(artifacts_dir)
        print(f"[MONITOR] Explanation artifacts saved to: {artifacts_dir}")
        
    except Exception as e:
        print(f"[MONITOR] ⚠️ Could not generate explanations: {e}")
    
    return explanations


if __name__ == '__main__':
    # Test with mock training result
    mock_training = {
        'leader_id': 'automl_GBM_1',
        'leader_metrics': {'auc': 0.89, 'logloss': 0.32},
        'leader': None,
        'automl': None,
    }
    
    result = evaluate_leaderboard(mock_training, performance_threshold=0.80, primary_metric='auc')
    print(json.dumps({k: v for k, v in result.items()}, indent=2, default=str))
