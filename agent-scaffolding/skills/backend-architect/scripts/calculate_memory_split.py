#!/usr/bin/env python3
"""
Calculate optimal JVM/Native memory split (Split-Memory Architect).

This script calculates the optimal memory allocation for hybrid
Java/Native workloads in containerized environments.

Usage:
    python calculate_memory_split.py --container-limit 16g --xgboost-estimate 4g --output jvm-args.env
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass 
class MemoryAllocation:
    """Represents a memory allocation recommendation."""
    container_limit_bytes: int
    jvm_heap_bytes: int
    native_headroom_bytes: int
    jvm_opts: str
    warnings: list


def parse_memory_size(size_str: str) -> int:
    """Parse a memory size string (e.g., '16g', '4096m') to bytes."""
    size_str = size_str.strip().lower()
    
    patterns = [
        (r'^(\d+(?:\.\d+)?)\s*gi?b?$', 1024 ** 3),
        (r'^(\d+(?:\.\d+)?)\s*mi?b?$', 1024 ** 2),
        (r'^(\d+(?:\.\d+)?)\s*ki?b?$', 1024),
        (r'^(\d+)$', 1),
    ]
    
    for pattern, multiplier in patterns:
        match = re.match(pattern, size_str)
        if match:
            return int(float(match.group(1)) * multiplier)
    
    raise ValueError(f"Cannot parse memory size: {size_str}")


def format_memory_size(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    if bytes_val >= 1024 ** 3:
        return f"{bytes_val / (1024 ** 3):.1f}g"
    elif bytes_val >= 1024 ** 2:
        return f"{bytes_val / (1024 ** 2):.0f}m"
    else:
        return f"{bytes_val}b"


def calculate_split(
    container_limit: int,
    xgboost_estimate: Optional[int] = None,
    jvm_ratio: float = 0.7
) -> MemoryAllocation:
    """Calculate optimal memory split between JVM heap and native."""
    warnings = []
    
    # Apply 70/30 split formula
    jvm_heap = int(container_limit * jvm_ratio)
    native_headroom = container_limit - jvm_heap
    
    # Validate against XGBoost requirements
    if xgboost_estimate:
        if xgboost_estimate > native_headroom:
            # Need more native headroom
            jvm_heap = container_limit - xgboost_estimate - (1024 ** 3)  # 1GB buffer
            native_headroom = container_limit - jvm_heap
            warnings.append(
                f"Reduced JVM heap to accommodate XGBoost requirement of {format_memory_size(xgboost_estimate)}"
            )
    
    # Validate minimums
    min_native = 2 * (1024 ** 3)  # 2GB minimum for native
    if native_headroom < min_native:
        warnings.append(
            f"Native headroom ({format_memory_size(native_headroom)}) below recommended 2GB minimum"
        )
    
    # Check for very small containers
    if container_limit < 4 * (1024 ** 3):
        warnings.append(
            f"Container limit ({format_memory_size(container_limit)}) is small for hybrid Java/XGBoost workloads"
        )
    
    # Format JVM options
    jvm_heap_mb = jvm_heap // (1024 ** 2)
    jvm_opts = f"-Xmx{jvm_heap_mb}m -Xms{jvm_heap_mb}m"
    
    return MemoryAllocation(
        container_limit_bytes=container_limit,
        jvm_heap_bytes=jvm_heap,
        native_headroom_bytes=native_headroom,
        jvm_opts=jvm_opts,
        warnings=warnings
    )


def analyze_compose_file(compose_file: Path) -> list:
    """Analyze a docker-compose file for memory configurations."""
    recommendations = []
    
    try:
        content = compose_file.read_text()
        
        # Find memory limits
        memory_matches = re.findall(r'memory:\s*(\d+[gGmM])', content)
        xmx_matches = re.findall(r'-Xmx(\d+[gGmM])', content)
        
        for mem, xmx in zip(memory_matches, xmx_matches):
            container_bytes = parse_memory_size(mem)
            xmx_bytes = parse_memory_size(xmx)
            
            ratio = xmx_bytes / container_bytes
            if ratio > 0.75:
                recommendations.append({
                    "container_limit": mem,
                    "current_xmx": xmx,
                    "issue": f"JVM heap is {ratio:.0%} of container; risk of OOM from native allocation",
                    "recommended": format_memory_size(int(container_bytes * 0.7))
                })
    except Exception as e:
        print(f"Error analyzing {compose_file}: {e}")
    
    return recommendations


def print_report(allocation: MemoryAllocation, output_format: str):
    """Print the allocation report."""
    if output_format == "json":
        data = {
            "container_limit": format_memory_size(allocation.container_limit_bytes),
            "jvm_heap": format_memory_size(allocation.jvm_heap_bytes),
            "native_headroom": format_memory_size(allocation.native_headroom_bytes),
            "jvm_opts": allocation.jvm_opts,
            "jvm_ratio": allocation.jvm_heap_bytes / allocation.container_limit_bytes,
            "warnings": allocation.warnings
        }
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("SPLIT-MEMORY ARCHITECT REPORT")
        print("=" * 60)
        print(f"""
Container Limit: {format_memory_size(allocation.container_limit_bytes)}

Memory Split (70/30 Formula):
├── JVM Heap (-Xmx): {format_memory_size(allocation.jvm_heap_bytes)} ({allocation.jvm_heap_bytes * 100 // allocation.container_limit_bytes}%)
└── Native Headroom: {format_memory_size(allocation.native_headroom_bytes)} ({allocation.native_headroom_bytes * 100 // allocation.container_limit_bytes}%)
    ├── XGBoost buffers
    ├── Python interpreter
    └── OS buffers

JVM Arguments: {allocation.jvm_opts}
""")
        
        if allocation.warnings:
            print("⚠️  Warnings:")
            for w in allocation.warnings:
                print(f"  • {w}")
            print()
        else:
            print("✅ Configuration looks safe for hybrid Java/Native workloads\n")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate optimal JVM/Native memory split"
    )
    parser.add_argument(
        "--container-limit", "-c",
        type=str,
        required=True,
        help="Container memory limit (e.g., 16g, 8192m)"
    )
    parser.add_argument(
        "--xgboost-estimate", "-x",
        type=str,
        help="Estimated XGBoost native memory requirement"
    )
    parser.add_argument(
        "--jvm-ratio", "-r",
        type=float,
        default=0.7,
        help="Ratio of container for JVM heap (default: 0.7)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json", "env"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write JVM args to file"
    )
    
    args = parser.parse_args()
    
    container_limit = parse_memory_size(args.container_limit)
    xgboost_estimate = parse_memory_size(args.xgboost_estimate) if args.xgboost_estimate else None
    
    allocation = calculate_split(container_limit, xgboost_estimate, args.jvm_ratio)
    
    if args.output == "env" or args.output_file:
        env_content = f"JAVA_OPTS={allocation.jvm_opts}\n"
        if args.output_file:
            args.output_file.write_text(env_content)
            print(f"Written to {args.output_file}")
        else:
            print(env_content)
    else:
        print_report(allocation, args.output)
    
    return 1 if allocation.warnings else 0


if __name__ == "__main__":
    sys.exit(main())
