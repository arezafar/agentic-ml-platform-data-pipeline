#!/usr/bin/env python3
"""
Mage OSS Pipeline Validator

Validates Mage pipeline structure including:
- Pipeline YAML/metadata structure
- Block type validation (data_loader, transformer, data_exporter)
- Block dependency validation
- Circular dependency detection

Usage:
    python validate_pipeline.py <pipeline_directory>
    python validate_pipeline.py <metadata.yaml>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


class PipelineValidationError(Exception):
    """Custom exception for pipeline validation errors."""
    pass


class MagePipelineValidator:
    """Validates Mage OSS pipeline structure and dependencies."""
    
    VALID_BLOCK_TYPES = {
        'data_loader',
        'transformer', 
        'data_exporter',
        'sensor',
        'scratchpad',
        'custom',
        'callback',
        'conditional',
        'dbt',
        'extension',
        'markdown',
    }
    
    REQUIRED_BLOCK_FIELDS = {'name', 'type'}
    
    def __init__(self, pipeline_path: Path):
        self.pipeline_path = pipeline_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metadata: dict[str, Any] = {}
        self.blocks: list[dict[str, Any]] = []
        
    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        try:
            self._load_pipeline()
            self._validate_metadata()
            self._validate_blocks()
            self._validate_dependencies()
            self._detect_circular_dependencies()
            
            return len(self.errors) == 0
        except Exception as e:
            self.errors.append(f"Unexpected error during validation: {e}")
            return False
    
    def _load_pipeline(self) -> None:
        """Load pipeline metadata from YAML file."""
        if self.pipeline_path.is_dir():
            metadata_file = self.pipeline_path / 'metadata.yaml'
        else:
            metadata_file = self.pipeline_path
            
        if not metadata_file.exists():
            raise PipelineValidationError(
                f"Pipeline metadata not found: {metadata_file}"
            )
        
        with open(metadata_file, 'r') as f:
            self.metadata = yaml.safe_load(f) or {}
            
        self.blocks = self.metadata.get('blocks', [])
        
    def _validate_metadata(self) -> None:
        """Validate pipeline-level metadata."""
        if 'name' not in self.metadata:
            self.errors.append("Pipeline missing required field: 'name'")
            
        if 'type' not in self.metadata:
            self.warnings.append(
                "Pipeline missing 'type' field, defaulting to 'python'"
            )
            
        pipeline_type = self.metadata.get('type', 'python')
        valid_types = {'python', 'pyspark', 'streaming', 'integration'}
        if pipeline_type not in valid_types:
            self.errors.append(
                f"Invalid pipeline type '{pipeline_type}'. "
                f"Must be one of: {valid_types}"
            )
    
    def _validate_blocks(self) -> None:
        """Validate individual block definitions."""
        if not self.blocks:
            self.warnings.append("Pipeline has no blocks defined")
            return
            
        block_names = set()
        has_loader = False
        has_exporter = False
        
        for idx, block in enumerate(self.blocks):
            block_id = block.get('name', f'block_{idx}')
            
            # Check required fields
            for field in self.REQUIRED_BLOCK_FIELDS:
                if field not in block:
                    self.errors.append(
                        f"Block '{block_id}' missing required field: '{field}'"
                    )
            
            # Validate block type
            block_type = block.get('type', '')
            if block_type not in self.VALID_BLOCK_TYPES:
                self.errors.append(
                    f"Block '{block_id}' has invalid type '{block_type}'. "
                    f"Must be one of: {self.VALID_BLOCK_TYPES}"
                )
            
            # Track block types for pipeline completeness
            if block_type == 'data_loader':
                has_loader = True
            elif block_type == 'data_exporter':
                has_exporter = True
                
            # Check for duplicate names
            name = block.get('name', '')
            if name in block_names:
                self.errors.append(f"Duplicate block name: '{name}'")
            block_names.add(name)
            
            # Validate upstream references exist
            upstream = block.get('upstream_blocks', [])
            for up_block in upstream:
                if up_block not in block_names and not self._block_exists(up_block):
                    self.warnings.append(
                        f"Block '{block_id}' references unknown upstream: '{up_block}'"
                    )
        
        # Check for complete pipeline
        if not has_loader:
            self.warnings.append(
                "Pipeline has no data_loader block - consider adding one"
            )
        if not has_exporter:
            self.warnings.append(
                "Pipeline has no data_exporter block - data may not be persisted"
            )
    
    def _block_exists(self, name: str) -> bool:
        """Check if a block with given name exists in the pipeline."""
        return any(b.get('name') == name for b in self.blocks)
    
    def _validate_dependencies(self) -> None:
        """Validate block dependency structure."""
        block_names = {b.get('name') for b in self.blocks}
        
        for block in self.blocks:
            block_name = block.get('name', 'unknown')
            upstream = block.get('upstream_blocks', [])
            downstream = block.get('downstream_blocks', [])
            
            # Check upstream references
            for ref in upstream:
                if ref not in block_names:
                    self.errors.append(
                        f"Block '{block_name}' has invalid upstream reference: '{ref}'"
                    )
            
            # Check downstream references  
            for ref in downstream:
                if ref not in block_names:
                    self.errors.append(
                        f"Block '{block_name}' has invalid downstream reference: '{ref}'"
                    )
    
    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies in the block DAG."""
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for block in self.blocks:
            name = block.get('name', '')
            downstream = block.get('downstream_blocks', [])
            # Also infer downstream from other blocks' upstream
            graph[name] = list(downstream)
            
        # Also add edges from upstream_blocks (reverse direction)
        for block in self.blocks:
            name = block.get('name', '')
            for upstream in block.get('upstream_blocks', []):
                if upstream in graph:
                    if name not in graph[upstream]:
                        graph[upstream].append(name)
        
        # Detect cycles using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in graph}
        
        def has_cycle(node: str, path: list[str]) -> bool:
            if color[node] == GRAY:
                cycle_path = ' -> '.join(path + [node])
                self.errors.append(f"Circular dependency detected: {cycle_path}")
                return True
            if color[node] == BLACK:
                return False
                
            color[node] = GRAY
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor in color and has_cycle(neighbor, path):
                    return True
                    
            path.pop()
            color[node] = BLACK
            return False
        
        for node in graph:
            if color[node] == WHITE:
                has_cycle(node, [])
    
    def get_report(self) -> str:
        """Generate a validation report."""
        lines = [
            "=" * 60,
            "MAGE PIPELINE VALIDATION REPORT",
            "=" * 60,
            f"Pipeline: {self.metadata.get('name', 'Unknown')}",
            f"Path: {self.pipeline_path}",
            f"Blocks: {len(self.blocks)}",
            "",
        ]
        
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ❌ {err}")
            lines.append("")
            
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ⚠️  {warn}")
            lines.append("")
            
        if not self.errors and not self.warnings:
            lines.append("✅ Pipeline validation passed with no issues!")
            
        elif not self.errors:
            lines.append("✅ Pipeline is valid (with warnings)")
        else:
            lines.append("❌ Pipeline validation FAILED")
            
        lines.append("=" * 60)
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Mage OSS pipeline structure'
    )
    parser.add_argument(
        'pipeline_path',
        type=str,
        help='Path to pipeline directory or metadata.yaml file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--strict',
        action='store_true', 
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    pipeline_path = Path(args.pipeline_path)
    if not pipeline_path.exists():
        print(f"Error: Path not found: {pipeline_path}", file=sys.stderr)
        sys.exit(1)
        
    validator = MagePipelineValidator(pipeline_path)
    is_valid = validator.validate()
    
    if args.strict and validator.warnings:
        is_valid = False
    
    if args.json:
        result = {
            'valid': is_valid,
            'pipeline': validator.metadata.get('name', 'Unknown'),
            'path': str(pipeline_path),
            'block_count': len(validator.blocks),
            'errors': validator.errors,
            'warnings': validator.warnings,
        }
        print(json.dumps(result, indent=2))
    else:
        print(validator.get_report())
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
