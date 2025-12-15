"""
Job 2: Model Registry & Artifact Export

Mage Data Exporter that:
1. Exports MOJO artifact (NOT POJO - avoid compilation overhead)
2. Logs metadata to PostgreSQL model_versions table
3. Triggers FastAPI hot-swap webhook

Success Criteria:
- .mojo file exists in output directory
- h2o-genmodel.jar is bundled for C++ runtime compatibility
- Model lineage tracked in database
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json
import requests


def export_to_registry(
    leader_result: Dict[str, Any],
    *args,
    **kwargs,
) -> Dict[str, Any]:
    """
    Export winning model to registry and trigger hot-swap.
    
    AD-001: Use MOJO over POJO/Pickle for production.
    MOJO is version-agnostic and supports C++ runtime.
    """
    from os import environ
    
    output_dir = Path(kwargs.get('output_dir', environ.get('MODEL_OUTPUT_PATH', '/models')))
    api_url = kwargs.get('api_url', environ.get('FASTAPI_URL', 'http://fastapi:8000'))
    reload_token = kwargs.get('reload_token', environ.get('RELOAD_TOKEN', 'dev-token'))
    
    leader = leader_result.get('leader', {})
    leader_id = leader_result.get('leader', {}).get('leader_id') or leader_result.get('leader_id', 'unknown')
    
    # Generate version
    version = datetime.now().strftime('%Y%m%d_%H%M%S')
    version_dir = output_dir / 'production' / version
    
    print(f"[REGISTRY] Exporting model to: {version_dir}")
    
    export_result = {
        'version': version,
        'model_id': leader_id,
        'artifacts': {},
        'registry_logged': False,
        'hot_swap_triggered': False,
    }
    
    try:
        import h2o
        
        model = leader_result.get('leader', {}).get('leader')
        if model is None:
            raise ValueError("No leader model available")
        
        # Create output directory
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Export MOJO (AD-001: Use MOJO over POJO)
        print(f"[REGISTRY] Exporting MOJO for: {leader_id}")
        mojo_path = model.download_mojo(
            path=str(version_dir),
            get_genmodel_jar=True,  # Required for C++ runtime
        )
        
        export_result['artifacts']['mojo'] = mojo_path
        print(f"[REGISTRY] ✅ MOJO exported: {mojo_path}")
        
        # Find genmodel JAR
        genmodel_jars = list(version_dir.glob("h2o-genmodel*.jar"))
        if genmodel_jars:
            export_result['artifacts']['genmodel_jar'] = str(genmodel_jars[0])
        
        # Create symlinks for production
        _update_production_symlinks(output_dir, version_dir, version)
        
        export_result['success'] = True
        
    except ImportError:
        print("[REGISTRY] ⚠️ H2O not available. Creating mock export.")
        export_result = _mock_export(version_dir, leader_id, version)
    
    # Log to model registry (PostgreSQL)
    registry_metadata = _log_to_registry(leader_result, export_result, kwargs)
    export_result['registry_logged'] = registry_metadata.get('logged', False)
    
    # Trigger FastAPI hot-swap
    if export_result.get('success'):
        hot_swap_result = _trigger_hot_swap(api_url, reload_token)
        export_result['hot_swap_triggered'] = hot_swap_result.get('triggered', False)
    
    return export_result


def _update_production_symlinks(base_dir: Path, version_dir: Path, version: str) -> None:
    """Update production symlinks to latest version."""
    prod_dir = base_dir / 'production'
    prod_dir.mkdir(parents=True, exist_ok=True)
    
    # Update symlinks
    for artifact_name in ['model.mojo', 'h2o-genmodel.jar']:
        artifacts = list(version_dir.glob(f"*{artifact_name.split('.')[-1]}"))
        if artifacts:
            link = prod_dir / artifact_name
            if link.is_symlink():
                link.unlink()
            link.symlink_to(artifacts[0].resolve())
    
    # Write version file
    (prod_dir / 'VERSION').write_text(version)
    print(f"[REGISTRY] Production symlinks updated: {version}")


def _log_to_registry(
    leader_result: Dict,
    export_result: Dict,
    config: Dict,
) -> Dict[str, Any]:
    """Log model metadata to PostgreSQL registry."""
    from os import environ
    
    try:
        import psycopg2
        import json
        
        conn = psycopg2.connect(
            host=environ.get('POSTGRES_HOST', 'postgres'),
            port=int(environ.get('POSTGRES_PORT', 5432)),
            database=environ.get('POSTGRES_DBNAME', 'mlops'),
            user=environ.get('POSTGRES_USER', 'postgres'),
            password=environ.get('POSTGRES_PASSWORD', 'postgres'),
        )
        
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_versions (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) UNIQUE,
                model_id VARCHAR(255),
                mojo_path TEXT,
                metrics JSONB,
                config JSONB,
                training_duration_secs FLOAT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Insert record
        cursor.execute("""
            INSERT INTO model_versions (version, model_id, mojo_path, metrics, config, training_duration_secs)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (version) DO UPDATE SET
                model_id = EXCLUDED.model_id,
                mojo_path = EXCLUDED.mojo_path,
                metrics = EXCLUDED.metrics
        """, (
            export_result['version'],
            export_result['model_id'],
            export_result['artifacts'].get('mojo'),
            json.dumps(leader_result.get('leader_metrics', {})),
            json.dumps(config),
            leader_result.get('training_duration_secs', 0),
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[REGISTRY] ✅ Logged to model_versions table")
        return {'logged': True}
        
    except Exception as e:
        print(f"[REGISTRY] ⚠️ Registry logging failed: {e}")
        return {'logged': False, 'error': str(e)}


def _trigger_hot_swap(api_url: str, token: str) -> Dict[str, Any]:
    """Trigger FastAPI model reload via webhook."""
    try:
        response = requests.post(
            f"{api_url}/system/reload-model",
            json={'invalidate_cache': True},
            headers={'X-Reload-Token': token},
            timeout=30,
        )
        
        if response.status_code == 200:
            print(f"[REGISTRY] ✅ Hot-swap triggered")
            return {'triggered': True, 'response': response.json()}
        else:
            print(f"[REGISTRY] ⚠️ Hot-swap failed: {response.status_code}")
            return {'triggered': False, 'status': response.status_code}
            
    except Exception as e:
        print(f"[REGISTRY] ⚠️ Hot-swap request failed: {e}")
        return {'triggered': False, 'error': str(e)}


def _mock_export(version_dir: Path, model_id: str, version: str) -> Dict[str, Any]:
    """Create mock export for testing."""
    version_dir.mkdir(parents=True, exist_ok=True)
    
    mojo_path = version_dir / 'model.mojo'
    mojo_path.write_text(f"MOCK MOJO: {model_id}")
    
    return {
        'version': version,
        'model_id': model_id,
        'artifacts': {'mojo': str(mojo_path)},
        'mock': True,
        'success': True,
    }


if __name__ == '__main__':
    mock_leader = {
        'leader_id': 'test_GBM_1',
        'leader_metrics': {'auc': 0.89},
        'training_duration_secs': 300,
    }
    result = export_to_registry(mock_leader, output_dir='/tmp/registry_test')
    print(json.dumps(result, indent=2))
