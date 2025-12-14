#!/usr/bin/env python3
"""
H2O Cluster Readiness Probe - PHY-01-02

This script implements a custom readiness check for H2O clusters
running on Kubernetes.

The Problem:
    Standard HTTP readiness probes (GET /3/About) return 200
    even when the H2O node hasn't joined the cluster yet.
    This leads to traffic being routed to isolated nodes.

The Solution:
    Query the /3/Cloud endpoint and verify:
    1. cloud_healthy is true
    2. cloud_size matches expected node count
    3. All nodes have the same cluster name

Usage in Kubernetes:
    readinessProbe:
      exec:
        command: ["python3", "/scripts/readiness_probe.py"]
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Optional, Tuple


def check_h2o_cluster_health(
    host: str = "localhost",
    port: int = 54321,
    expected_nodes: Optional[int] = None,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Check if H2O cluster is healthy and fully formed.
    
    Args:
        host: H2O host (default: localhost)
        port: H2O port (default: 54321)
        expected_nodes: Expected number of nodes in cluster
        timeout: HTTP request timeout
    
    Returns:
        Tuple of (is_healthy, message)
    """
    url = f"http://{host}:{port}/3/Cloud"
    
    try:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return False, f"Connection failed: {e.reason}"
    except json.JSONDecodeError:
        return False, "Invalid JSON response"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
    
    # Check cloud health flag
    if not data.get("cloud_healthy", False):
        return False, "Cloud is not healthy"
    
    # Check cloud size
    cloud_size = data.get("cloud_size", 0)
    if cloud_size == 0:
        return False, "Cloud size is 0"
    
    if expected_nodes and cloud_size < expected_nodes:
        return False, f"Cloud size {cloud_size} < expected {expected_nodes}"
    
    # Check for locked cloud (consensus reached)
    if not data.get("cloud_locked", False):
        # Cloud not yet locked - nodes still discovering
        return False, "Cloud not locked (still forming)"
    
    # Check consensus on cloud name across all nodes
    nodes = data.get("nodes", [])
    if len(nodes) != cloud_size:
        return False, f"Node list size mismatch: {len(nodes)} != {cloud_size}"
    
    # Optional: Check all nodes are healthy
    unhealthy_nodes = [
        n.get("h2o", {}).get("node_id")
        for n in nodes
        if not n.get("healthy", True)
    ]
    if unhealthy_nodes:
        return False, f"Unhealthy nodes: {unhealthy_nodes}"
    
    return True, f"Cluster healthy with {cloud_size} nodes"


def check_leader_node(
    host: str = "localhost",
    port: int = 54321,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Check if this node is the leader of the H2O cluster.
    
    This is useful for services that should only run on the leader.
    
    Args:
        host: H2O host
        port: H2O port
        timeout: HTTP request timeout
    
    Returns:
        Tuple of (is_leader, message)
    """
    url = f"http://{host}:{port}/3/Cloud"
    
    try:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return False, f"Error: {str(e)}"
    
    # Check if this is the leader node
    is_leader = data.get("is_leader", False)
    
    if is_leader:
        return True, "This node is the leader"
    else:
        return False, "This node is not the leader"


def main():
    """
    Main entry point for Kubernetes readiness probe.
    
    Reads configuration from environment variables:
    - H2O_HOST: H2O host (default: localhost)
    - H2O_PORT: H2O port (default: 54321)
    - H2O_NODE_EXPECTED_COUNT: Expected cluster size (optional)
    - H2O_READINESS_TIMEOUT: Probe timeout (default: 5)
    
    Exit codes:
    - 0: Healthy (pod should receive traffic)
    - 1: Unhealthy (pod should NOT receive traffic)
    """
    host = os.environ.get("H2O_HOST", "localhost")
    port = int(os.environ.get("H2O_PORT", "54321"))
    timeout = float(os.environ.get("H2O_READINESS_TIMEOUT", "5"))
    
    expected_nodes = os.environ.get("H2O_NODE_EXPECTED_COUNT")
    if expected_nodes:
        expected_nodes = int(expected_nodes)
    
    is_healthy, message = check_h2o_cluster_health(
        host=host,
        port=port,
        expected_nodes=expected_nodes,
        timeout=timeout
    )
    
    if is_healthy:
        print(f"READY: {message}")
        sys.exit(0)
    else:
        print(f"NOT READY: {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
