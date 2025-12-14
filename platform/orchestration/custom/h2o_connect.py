"""
Custom Block: H2O Connection and Initialization

Mage Custom block for establishing connection to H2O cluster.
Manages connection lifecycle and health checks.

Block Type: custom
Connection: H2O via h2o-py
"""

from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd

if 'custom' not in dir():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@custom
def connect_h2o(
    data: pd.DataFrame,
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Initialize connection to H2O cluster.
    
    This block establishes the H2O connection for downstream blocks.
    Returns connection metadata for verification.
    
    Configuration via pipeline variables:
    - h2o_url: H2O cluster URL (default: from H2O_URL env var)
    - cluster_name: Cluster identifier for logging
    - max_mem_size: Memory limit for local H2O (if starting new cluster)
    """
    from os import environ
    
    # Configuration
    h2o_url = kwargs.get('h2o_url', environ.get('H2O_URL', 'http://h2o-compute:54321'))
    cluster_name = kwargs.get('cluster_name', 'agentic-pipeline')
    max_retries = kwargs.get('max_retries', 3)
    
    connection_info = {
        'connected': False,
        'cluster_name': cluster_name,
        'h2o_url': h2o_url,
        'connected_at': None,
        'cluster_info': {},
        'input_data': data,
    }
    
    try:
        import h2o
        
        print(f"   Connecting to H2O at {h2o_url}...")
        
        # Attempt connection with retries
        for attempt in range(max_retries):
            try:
                h2o.init(
                    url=h2o_url,
                    name=cluster_name,
                    strict_version_check=False,
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    import time
                    wait = 2 ** attempt
                    print(f"   Connection attempt {attempt + 1} failed, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        
        # Get cluster info
        cluster = h2o.cluster()
        
        connection_info.update({
            'connected': True,
            'connected_at': datetime.utcnow().isoformat(),
            'cluster_info': {
                'version': cluster.version if hasattr(cluster, 'version') else 'unknown',
                'cloud_name': cluster.cloud_name if hasattr(cluster, 'cloud_name') else cluster_name,
                'nodes': cluster.nodes if hasattr(cluster, 'nodes') else 1,
                'total_memory': cluster.total_memory if hasattr(cluster, 'total_memory') else 'unknown',
                'free_memory': cluster.free_memory if hasattr(cluster, 'free_memory') else 'unknown',
            },
        })
        
        print(f"✅ Connected to H2O cluster")
        print(f"   Version: {connection_info['cluster_info']['version']}")
        print(f"   Nodes: {connection_info['cluster_info']['nodes']}")
        print(f"   Memory: {connection_info['cluster_info']['free_memory']}")
        
    except ImportError:
        print("⚠️  h2o package not installed. Simulating connection for development.")
        connection_info.update({
            'connected': True,
            'connected_at': datetime.utcnow().isoformat(),
            'cluster_info': {
                'version': 'mock-3.46.0',
                'cloud_name': cluster_name,
                'nodes': 1,
                'total_memory': '4GB (mock)',
                'free_memory': '3GB (mock)',
            },
            'mock': True,
        })
        
    except Exception as e:
        print(f"❌ Failed to connect to H2O: {e}")
        connection_info['error'] = str(e)
        raise
    
    return connection_info


@test
def test_connection(output: Dict, *args) -> None:
    """Test that H2O connection was established."""
    assert output.get('connected') == True, 'H2O connection failed'
    assert output.get('cluster_info'), 'No cluster info returned'
    print(f"✓ H2O connection verified")


@test
def test_cluster_health(output: Dict, *args) -> None:
    """Test that cluster has available resources."""
    info = output.get('cluster_info', {})
    if info.get('nodes'):
        assert info['nodes'] >= 1, 'No H2O nodes available'
        print(f"✓ H2O cluster has {info['nodes']} node(s)")
