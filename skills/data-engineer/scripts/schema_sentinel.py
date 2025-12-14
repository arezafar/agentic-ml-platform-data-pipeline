#!/usr/bin/env python3
"""
Schema Sentinel - Autonomous Schema Evolution

JTBD Domain 1: Intelligent Ingestion (The Gatekeeper)

Detects upstream schema changes, calculates "Schema Delta," and 
executes ALTER TABLE commands or quarantines non-compliant data.

Features:
- Schema inference from data samples
- Delta detection (new columns, type changes, removed columns)
- DDL generation for ALTER TABLE commands
- Quarantine routing for non-compliant batches

Usage:
    python schema_sentinel.py --source sample.json --target postgres://...
    python schema_sentinel.py --compare schema_v1.json schema_v2.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ChangeType(Enum):
    """Types of schema changes."""
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    DEFAULT_CHANGED = "default_changed"


class EvolutionStrategy(Enum):
    """Schema evolution strategies."""
    FAIL = "fail"           # Reject change, fail pipeline
    IGNORE = "ignore"       # Accept data, ignore schema diff
    APPEND = "append"       # Auto-add new columns
    SYNC = "sync"           # Full sync (dangerous: may drop columns)
    QUARANTINE = "quarantine"  # Route to quarantine table


@dataclass
class ColumnSchema:
    """Schema for a single column."""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'data_type': self.data_type,
            'nullable': self.nullable,
            'default': self.default,
            'description': self.description,
        }


@dataclass
class TableSchema:
    """Schema for a table."""
    name: str
    columns: dict[str, ColumnSchema] = field(default_factory=dict)
    version: str = "1.0.0"
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_column(self, col: ColumnSchema) -> None:
        self.columns[col.name] = col
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'version': self.version,
            'updated_at': self.updated_at,
            'columns': {k: v.to_dict() for k, v in self.columns.items()},
        }


@dataclass
class SchemaChange:
    """Represents a single schema change."""
    change_type: ChangeType
    column_name: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    severity: str = "info"  # info, warning, error, critical
    
    def to_dict(self) -> dict:
        return {
            'type': self.change_type.value,
            'column': self.column_name,
            'old': self.old_value,
            'new': self.new_value,
            'severity': self.severity,
        }


class SchemaSentinel:
    """Autonomous schema evolution agent."""
    
    # Type mapping from Python/JSON to PostgreSQL
    TYPE_MAPPING = {
        'str': 'TEXT',
        'string': 'TEXT',
        'int': 'BIGINT',
        'integer': 'BIGINT',
        'float': 'DOUBLE PRECISION',
        'number': 'DOUBLE PRECISION',
        'bool': 'BOOLEAN',
        'boolean': 'BOOLEAN',
        'list': 'JSONB',
        'array': 'JSONB',
        'dict': 'JSONB',
        'object': 'JSONB',
        'null': 'TEXT',
        'datetime': 'TIMESTAMPTZ',
        'date': 'DATE',
        'uuid': 'UUID',
    }
    
    # Type widening hierarchy (can safely cast from -> to)
    TYPE_WIDENING = {
        'INTEGER': ['BIGINT', 'DOUBLE PRECISION', 'TEXT'],
        'BIGINT': ['DOUBLE PRECISION', 'TEXT'],
        'DOUBLE PRECISION': ['TEXT'],
        'BOOLEAN': ['TEXT'],
        'DATE': ['TIMESTAMPTZ', 'TEXT'],
        'TIMESTAMPTZ': ['TEXT'],
        'UUID': ['TEXT'],
        'TEXT': [],  # TEXT is the widest
        'JSONB': ['TEXT'],
    }
    
    def __init__(self, strategy: EvolutionStrategy = EvolutionStrategy.APPEND):
        self.strategy = strategy
        self.changes: list[SchemaChange] = []
    
    def infer_schema(self, 
                     data: list[dict], 
                     table_name: str = "inferred_table") -> TableSchema:
        """Infer schema from a list of records.
        
        Args:
            data: List of dictionaries representing records
            table_name: Name for the inferred table
            
        Returns:
            Inferred TableSchema
        """
        if not data:
            return TableSchema(name=table_name)
        
        # Collect all columns and their types
        column_types: dict[str, set[str]] = {}
        column_nullable: dict[str, bool] = {}
        
        for record in data:
            for key, value in record.items():
                if key not in column_types:
                    column_types[key] = set()
                    column_nullable[key] = False
                
                if value is None:
                    column_nullable[key] = True
                else:
                    python_type = type(value).__name__
                    column_types[key].add(python_type)
        
        # Build schema
        schema = TableSchema(name=table_name)
        
        for col_name, types in column_types.items():
            # Resolve type conflicts by widening
            pg_type = self._resolve_type(types)
            
            schema.add_column(ColumnSchema(
                name=col_name,
                data_type=pg_type,
                nullable=column_nullable[col_name],
            ))
        
        return schema
    
    def _resolve_type(self, types: set[str]) -> str:
        """Resolve multiple Python types to a single PostgreSQL type."""
        if not types:
            return 'TEXT'
        
        pg_types = {self.TYPE_MAPPING.get(t.lower(), 'TEXT') for t in types}
        
        if len(pg_types) == 1:
            return pg_types.pop()
        
        # If mixed types, widen to most general
        if 'JSONB' in pg_types:
            return 'JSONB'
        if 'TEXT' in pg_types:
            return 'TEXT'
        if 'DOUBLE PRECISION' in pg_types:
            return 'DOUBLE PRECISION'
        if 'BIGINT' in pg_types:
            return 'BIGINT'
        
        return 'TEXT'
    
    def compare_schemas(self, 
                        source: TableSchema, 
                        target: TableSchema) -> list[SchemaChange]:
        """Compare two schemas and identify changes.
        
        Args:
            source: The incoming (new) schema
            target: The existing (current) schema
            
        Returns:
            List of schema changes
        """
        self.changes = []
        
        source_cols = set(source.columns.keys())
        target_cols = set(target.columns.keys())
        
        # New columns
        for col in source_cols - target_cols:
            self.changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                column_name=col,
                new_value=source.columns[col].data_type,
                severity='info',
            ))
        
        # Removed columns
        for col in target_cols - source_cols:
            self.changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                column_name=col,
                old_value=target.columns[col].data_type,
                severity='warning',
            ))
        
        # Modified columns
        for col in source_cols & target_cols:
            src_col = source.columns[col]
            tgt_col = target.columns[col]
            
            # Type change
            if src_col.data_type != tgt_col.data_type:
                severity = self._assess_type_change_severity(
                    tgt_col.data_type, src_col.data_type
                )
                self.changes.append(SchemaChange(
                    change_type=ChangeType.TYPE_CHANGED,
                    column_name=col,
                    old_value=tgt_col.data_type,
                    new_value=src_col.data_type,
                    severity=severity,
                ))
            
            # Nullable change
            if src_col.nullable != tgt_col.nullable:
                severity = 'warning' if not src_col.nullable else 'info'
                self.changes.append(SchemaChange(
                    change_type=ChangeType.NULLABLE_CHANGED,
                    column_name=col,
                    old_value=tgt_col.nullable,
                    new_value=src_col.nullable,
                    severity=severity,
                ))
        
        return self.changes
    
    def _assess_type_change_severity(self, 
                                      old_type: str, 
                                      new_type: str) -> str:
        """Assess the severity of a type change."""
        old_upper = old_type.upper()
        new_upper = new_type.upper()
        
        # Check if it's a safe widening
        if old_upper in self.TYPE_WIDENING:
            if new_upper in self.TYPE_WIDENING[old_upper]:
                return 'info'  # Safe widening
        
        # Check if it's a narrowing (dangerous)
        if new_upper in self.TYPE_WIDENING:
            if old_upper in self.TYPE_WIDENING[new_upper]:
                return 'error'  # Data loss possible
        
        return 'warning'  # Unknown transformation
    
    def generate_ddl(self, 
                     changes: list[SchemaChange], 
                     table_name: str) -> list[str]:
        """Generate ALTER TABLE statements for schema changes.
        
        Args:
            changes: List of schema changes
            table_name: Target table name
            
        Returns:
            List of DDL statements
        """
        statements = []
        
        for change in changes:
            if change.change_type == ChangeType.COLUMN_ADDED:
                stmt = (
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN IF NOT EXISTS {change.column_name} {change.new_value};"
                )
                statements.append(stmt)
            
            elif change.change_type == ChangeType.TYPE_CHANGED:
                if change.severity in ('info', 'warning'):
                    stmt = (
                        f"ALTER TABLE {table_name} "
                        f"ALTER COLUMN {change.column_name} "
                        f"TYPE {change.new_value} USING {change.column_name}::{change.new_value};"
                    )
                    statements.append(stmt)
                else:
                    statements.append(
                        f"-- MANUAL REVIEW REQUIRED: {change.column_name} "
                        f"type change from {change.old_value} to {change.new_value}"
                    )
            
            elif change.change_type == ChangeType.COLUMN_REMOVED:
                # Never auto-drop columns
                statements.append(
                    f"-- WARNING: Column '{change.column_name}' exists in target "
                    f"but not in source. Manual review required."
                )
        
        return statements
    
    def should_quarantine(self, changes: list[SchemaChange]) -> bool:
        """Determine if data should be quarantined based on changes."""
        if self.strategy == EvolutionStrategy.QUARANTINE:
            return any(c.severity in ('error', 'critical') for c in changes)
        return False
    
    def get_report(self, 
                   source: TableSchema, 
                   target: TableSchema,
                   changes: list[SchemaChange]) -> str:
        """Generate a human-readable schema delta report."""
        lines = [
            "=" * 60,
            "SCHEMA SENTINEL REPORT",
            "=" * 60,
            f"Source Schema: {source.name} (v{source.version})",
            f"Target Schema: {target.name} (v{target.version})",
            f"Strategy: {self.strategy.value}",
            f"Changes Detected: {len(changes)}",
            "",
        ]
        
        if changes:
            # Group by severity
            by_severity = {'critical': [], 'error': [], 'warning': [], 'info': []}
            for c in changes:
                by_severity[c.severity].append(c)
            
            for severity, items in by_severity.items():
                if items:
                    icon = {'critical': '🔴', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}[severity]
                    lines.append(f"{severity.upper()} ({len(items)}):")
                    for c in items:
                        lines.append(f"  {icon} {c.change_type.value}: {c.column_name}")
                        if c.old_value and c.new_value:
                            lines.append(f"      {c.old_value} → {c.new_value}")
                    lines.append("")
            
            # Recommendation
            if self.should_quarantine(changes):
                lines.append("⚠️  RECOMMENDATION: Quarantine this batch for manual review")
            else:
                lines.append("✅ RECOMMENDATION: Safe to proceed with evolution")
        else:
            lines.append("✅ No schema changes detected")
        
        lines.append("=" * 60)
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Schema Sentinel - Autonomous Schema Evolution')
    parser.add_argument('--source', type=str, help='Source data/schema file (JSON)')
    parser.add_argument('--target', type=str, help='Target schema file (JSON)')
    parser.add_argument('--compare', nargs=2, help='Compare two schema files')
    parser.add_argument('--strategy', type=str, 
                        choices=['fail', 'ignore', 'append', 'sync', 'quarantine'],
                        default='append')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--ddl', action='store_true', help='Generate DDL statements')
    
    args = parser.parse_args()
    
    sentinel = SchemaSentinel(
        strategy=EvolutionStrategy(args.strategy)
    )
    
    if args.compare:
        # Compare two schema files
        with open(args.compare[0]) as f:
            schema1_data = json.load(f)
        with open(args.compare[1]) as f:
            schema2_data = json.load(f)
        
        # Convert to TableSchema objects
        source = TableSchema(name=schema1_data.get('name', 'source'))
        for col_name, col_data in schema1_data.get('columns', {}).items():
            source.add_column(ColumnSchema(
                name=col_name,
                data_type=col_data.get('data_type', 'TEXT'),
                nullable=col_data.get('nullable', True),
            ))
        
        target = TableSchema(name=schema2_data.get('name', 'target'))
        for col_name, col_data in schema2_data.get('columns', {}).items():
            target.add_column(ColumnSchema(
                name=col_name,
                data_type=col_data.get('data_type', 'TEXT'),
                nullable=col_data.get('nullable', True),
            ))
        
    elif args.source:
        # Infer schema from data
        with open(args.source) as f:
            data = json.load(f)
        
        if isinstance(data, list):
            source = sentinel.infer_schema(data, "inferred")
        else:
            source = sentinel.infer_schema([data], "inferred")
        
        if args.target:
            with open(args.target) as f:
                target_data = json.load(f)
            target = TableSchema(name=target_data.get('name', 'target'))
            for col_name, col_data in target_data.get('columns', {}).items():
                target.add_column(ColumnSchema(
                    name=col_name,
                    data_type=col_data.get('data_type', 'TEXT'),
                    nullable=col_data.get('nullable', True),
                ))
        else:
            target = TableSchema(name="empty")
    else:
        parser.print_help()
        sys.exit(1)
    
    changes = sentinel.compare_schemas(source, target)
    
    if args.json:
        output = {
            'source': source.to_dict(),
            'target': target.to_dict(),
            'changes': [c.to_dict() for c in changes],
            'should_quarantine': sentinel.should_quarantine(changes),
        }
        if args.ddl:
            output['ddl'] = sentinel.generate_ddl(changes, target.name)
        print(json.dumps(output, indent=2))
    else:
        print(sentinel.get_report(source, target, changes))
        
        if args.ddl and changes:
            print("\nGENERATED DDL:")
            for stmt in sentinel.generate_ddl(changes, target.name):
                print(f"  {stmt}")
    
    # Exit with error if quarantine recommended
    if sentinel.should_quarantine(changes):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
