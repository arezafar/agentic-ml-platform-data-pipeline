"""
Job 2: Artifact Management Exporter

Mage Data Exporter Block for serializing the winning model.
Downloads MOJO artifact and persists with metadata to shared
volume or object storage.

Success Criteria:
- .zip or .mojo file exists in output directory
- Model lineage is tracked in Mage
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json


def export_model_artifacts(training_result: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Export winning model as MOJO artifact.
    
    Serializes the leader model from AutoML training and persists
    it along with metadata for production deployment.
    
    Outputs:
    - MOJO artifact (.zip or .mojo)
    - GenModel JAR for standalone scoring
    - Metadata JSON (feature list, scaler logic, lineage)
    
    Args:
        training_result: Output from training_agent block
        
    Returns:
        Dictionary with artifact paths and metadata
    """
    from os import environ
    
    output_dir = Path(kwargs.get('output_dir', environ.get('MODEL_OUTPUT_PATH', '/models')))
    model_name = kwargs.get('model_name', 'production_model')
    
    print(f"[ARTIFACT-EXPORT] Exporting model artifacts to: {output_dir}")
    
    # Extract training information
    tr = training_result.get('training_result', {})
    leader = tr.get('leader')
    leader_id = tr.get('leader_id', 'unknown')
    
    # Generate version for lineage tracking
    version = datetime.now().strftime('%Y%m%d_%H%M%S')
    version_dir = output_dir / 'production' / version
    
    export_result = {
        'version': version,
        'model_id': leader_id,
        'artifacts': {},
        'lineage': {},
        'exported_at': datetime.utcnow().isoformat(),
    }
    
    try:
        import h2o
        
        if leader is None:
            raise ValueError("No leader model available for export")
        
        # Create output directory
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Export MOJO artifact
        print(f"[ARTIFACT-EXPORT] Exporting MOJO for: {leader_id}")
        mojo_path = leader.download_mojo(
            path=str(version_dir),
            get_genmodel_jar=True,
        )
        
        export_result['artifacts']['mojo'] = mojo_path
        print(f"[ARTIFACT-EXPORT] ✅ MOJO saved: {mojo_path}")
        
        # Find genmodel JAR
        genmodel_jars = list(version_dir.glob("h2o-genmodel*.jar"))
        if genmodel_jars:
            export_result['artifacts']['genmodel_jar'] = str(genmodel_jars[0])
            print(f"[ARTIFACT-EXPORT] ✅ GenModel JAR saved: {genmodel_jars[0]}")
        
        # Extract feature list
        feature_list = tr.get('predictors', [])
        
        # Build lineage metadata
        lineage = {
            'model_id': leader_id,
            'algorithm': type(leader).__name__,
            'version': version,
            'training_duration_secs': tr.get('training_duration_secs'),
            'models_evaluated': tr.get('models_trained'),
            'features': feature_list,
            'feature_count': len(feature_list),
            'training_config': training_result.get('config', {}),
            'created_at': datetime.utcnow().isoformat(),
        }
        
        # Save lineage metadata
        lineage_path = version_dir / 'model_lineage.json'
        with open(lineage_path, 'w') as f:
            json.dump(lineage, f, indent=2)
        
        export_result['artifacts']['lineage'] = str(lineage_path)
        export_result['lineage'] = lineage
        
        print(f"[ARTIFACT-EXPORT] ✅ Lineage saved: {lineage_path}")
        
        # Update production symlinks
        _update_production_symlinks(output_dir, version_dir)
        
        export_result['success'] = True
        
    except ImportError:
        print("[ARTIFACT-EXPORT] ⚠️ H2O not available. Creating mock artifacts.")
        export_result = _mock_export(version_dir, leader_id, version, tr)
        
    except Exception as e:
        print(f"[ARTIFACT-EXPORT] ❌ Export failed: {e}")
        export_result['success'] = False
        export_result['error'] = str(e)
    
    return export_result


def _update_production_symlinks(base_dir: Path, version_dir: Path) -> None:
    """Update production symlinks to point to latest version."""
    prod_dir = base_dir / 'production'
    prod_dir.mkdir(parents=True, exist_ok=True)
    
    # Create/update symlinks
    for artifact in ['model.mojo', 'h2o-genmodel.jar', 'model_lineage.json']:
        link = prod_dir / artifact
        target = list(version_dir.glob(f"*{artifact.split('.')[-1]}"))
        
        if target:
            if link.is_symlink():
                link.unlink()
            link.symlink_to(target[0].resolve())
            print(f"[ARTIFACT-EXPORT] Symlink updated: {artifact}")
    
    # Write current version file
    version_file = prod_dir / 'CURRENT_VERSION'
    version_file.write_text(version_dir.name)


def _mock_export(version_dir: Path, model_id: str, version: str, tr: Dict) -> Dict[str, Any]:
    """Create mock export for testing without H2O."""
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock MOJO file
    mojo_path = version_dir / 'model.mojo'
    mojo_path.write_text(f"MOCK MOJO: {model_id}")
    
    # Create mock lineage
    lineage = {
        'model_id': model_id,
        'algorithm': 'MockGBM',
        'version': version,
        'features': tr.get('predictors', ['feature_1', 'feature_2']),
        'mock': True,
    }
    
    lineage_path = version_dir / 'model_lineage.json'
    with open(lineage_path, 'w') as f:
        json.dump(lineage, f, indent=2)
    
    return {
        'version': version,
        'model_id': model_id,
        'artifacts': {
            'mojo': str(mojo_path),
            'lineage': str(lineage_path),
        },
        'lineage': lineage,
        'mock': True,
        'success': True,
    }


if __name__ == '__main__':
    mock_training_result = {
        'training_result': {
            'leader': None,
            'leader_id': 'test_GBM_1',
            'predictors': ['feature_1', 'feature_2'],
            'training_duration_secs': 100,
            'models_trained': 10,
        },
        'config': {'max_models': 20},
    }
    
    result = export_model_artifacts(mock_training_result, output_dir='/tmp/model_export_test')
    print(json.dumps(result, indent=2))
