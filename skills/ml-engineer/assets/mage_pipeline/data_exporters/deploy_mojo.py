"""
JTBD Step 8: Conclude - MOJO Export & Deployment

The finalization step where the solution is delivered to end-users.
Implements:
- MOJO artifact generation (low-latency Java binary)
- genmodel.jar bundling for self-contained deployment
- Model versioning and archival
- Serving container update trigger
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json
import shutil


def deploy_mojo(training_result: Dict[str, Any], evaluation: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Export leader model as MOJO and deploy to serving container.
    
    MOJO (Model Object, Optimized) is the production deployment format:
    - Standalone Java object without full H2O cluster
    - Significantly lower latency than binary format
    - Version-agnostic (mostly compatible across H2O versions)
    
    Args:
        training_result: Output from train_automl block
        evaluation: Output from evaluate_leaderboard block
        
    Returns:
        Dictionary with deployment artifacts and status
    """
    from os import environ
    
    # Check if approved for deployment
    decision = evaluation.get('decision', '')
    if decision != 'APPROVE_FOR_DEPLOYMENT':
        print(f"[CONCLUDE] ⚠️ Model not approved for deployment: {decision}")
        return {
            'deployed': False,
            'reason': f"Not approved: {decision}",
        }
    
    # Configuration
    output_dir = Path(kwargs.get('mojo_output_dir', environ.get('MODEL_OUTPUT_PATH', '/models/production')))
    enable_versioning = kwargs.get('enable_versioning', True)
    model_name = kwargs.get('model_name', 'model')
    
    print(f"[CONCLUDE] Deploying MOJO to: {output_dir}")
    
    leader = training_result.get('leader')
    leader_id = training_result.get('leader_id', 'unknown')
    
    deployment = {
        'model_id': leader_id,
        'deployed': False,
        'mojo_path': None,
        'genmodel_path': None,
        'version': None,
        'deployed_at': None,
    }
    
    try:
        import h2o
        
        if leader is None:
            raise ValueError("No leader model available for deployment")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate version string
        if enable_versioning:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
            versioned_dir = output_dir / version
            versioned_dir.mkdir(parents=True, exist_ok=True)
            target_dir = versioned_dir
        else:
            target_dir = output_dir
        
        # Export MOJO
        print(f"[CONCLUDE] Exporting MOJO for: {leader_id}")
        mojo_path = leader.download_mojo(
            path=str(target_dir),
            get_genmodel_jar=True,
        )
        
        # Find the genmodel.jar
        genmodel_jar = list(target_dir.glob("h2o-genmodel*.jar"))
        genmodel_path = str(genmodel_jar[0]) if genmodel_jar else None
        
        # Create symlinks for "latest"
        latest_mojo = output_dir / "model.mojo"
        latest_genmodel = output_dir / "h2o-genmodel.jar"
        
        # Remove existing symlinks
        for link in [latest_mojo, latest_genmodel]:
            if link.is_symlink() or link.exists():
                link.unlink()
        
        # Create new symlinks
        if Path(mojo_path).exists():
            latest_mojo.symlink_to(Path(mojo_path).resolve())
        if genmodel_path and Path(genmodel_path).exists():
            latest_genmodel.symlink_to(Path(genmodel_path).resolve())
        
        # Save metadata
        metadata = {
            'model_id': leader_id,
            'algorithm': str(type(leader).__name__) if leader else 'unknown',
            'metrics': training_result.get('leader_metrics', {}),
            'version': version if enable_versioning else 'latest',
            'mojo_path': str(mojo_path),
            'genmodel_path': genmodel_path,
            'deployed_at': datetime.utcnow().isoformat(),
            'training_duration_secs': training_result.get('training_duration_secs'),
            'predictors': training_result.get('predictors', []),
        }
        
        metadata_path = target_dir / "model_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        deployment = {
            'model_id': leader_id,
            'deployed': True,
            'mojo_path': str(mojo_path),
            'genmodel_path': genmodel_path,
            'metadata_path': str(metadata_path),
            'version': version if enable_versioning else 'latest',
            'deployed_at': datetime.utcnow().isoformat(),
        }
        
        print(f"[CONCLUDE] ✅ MOJO deployed successfully!")
        print(f"[CONCLUDE]   Path: {mojo_path}")
        print(f"[CONCLUDE]   Version: {deployment['version']}")
        
        # Trigger serving container reload (conceptual)
        _trigger_serving_reload(output_dir)
        
    except ImportError:
        print("[CONCLUDE] ⚠️ H2O not available. Simulating MOJO export.")
        deployment = _mock_deployment(leader_id, output_dir, enable_versioning)
        
    except Exception as e:
        print(f"[CONCLUDE] ❌ Deployment failed: {e}")
        deployment['error'] = str(e)
    
    return deployment


def _trigger_serving_reload(model_dir: Path) -> None:
    """
    Signal the serving container to reload the model.
    
    In a real deployment, this might:
    - Call a serving container API
    - Trigger a CI/CD pipeline
    - Restart the container via Docker API
    """
    trigger_file = model_dir / ".reload_trigger"
    trigger_file.write_text(datetime.utcnow().isoformat())
    print(f"[CONCLUDE] Serving reload triggered: {trigger_file}")


def _mock_deployment(model_id: str, output_dir: Path, versioning: bool) -> Dict[str, Any]:
    """Mock deployment for testing without H2O."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    version = datetime.now().strftime('%Y%m%d_%H%M%S') if versioning else 'latest'
    
    # Create mock files
    mock_mojo = output_dir / "model.mojo"
    mock_mojo.write_text(f"MOCK MOJO: {model_id}")
    
    return {
        'model_id': model_id,
        'deployed': True,
        'mojo_path': str(mock_mojo),
        'genmodel_path': None,
        'version': version,
        'deployed_at': datetime.utcnow().isoformat(),
        'mock': True,
    }


if __name__ == '__main__':
    # Test with mock data
    mock_training = {
        'leader': None,
        'leader_id': 'test_GBM_1',
        'leader_metrics': {'auc': 0.89},
    }
    mock_eval = {'decision': 'APPROVE_FOR_DEPLOYMENT'}
    
    result = deploy_mojo(mock_training, mock_eval, mojo_output_dir='/tmp/mojo_test')
    print(json.dumps(result, indent=2))
