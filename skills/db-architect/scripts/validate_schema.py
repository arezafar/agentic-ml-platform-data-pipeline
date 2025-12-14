#!/usr/bin/env python3
"""
PostgreSQL Schema Validator

Validates JSON schema definitions for PostgreSQL databases including:
- Primary key presence on all tables
- Foreign key reference validity
- Circular foreign key detection
- Naming convention enforcement
- Basic normalization checks (3NF)

Usage:
    python validate_schema.py <schema.json>
    python validate_schema.py <schema.json> --strict
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    pass


class PostgresSchemaValidator:
    """Validates JSON schema definitions for PostgreSQL databases."""
    
    # Naming conventions
    TABLE_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    COLUMN_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    
    # Reserved PostgreSQL keywords (subset)
    RESERVED_KEYWORDS = {
        'all', 'analyse', 'analyze', 'and', 'any', 'array', 'as', 'asc',
        'asymmetric', 'both', 'case', 'cast', 'check', 'collate', 'column',
        'constraint', 'create', 'current_date', 'current_role', 'current_time',
        'current_timestamp', 'current_user', 'default', 'deferrable', 'desc',
        'distinct', 'do', 'else', 'end', 'except', 'false', 'for', 'foreign',
        'from', 'grant', 'group', 'having', 'in', 'initially', 'intersect',
        'into', 'is', 'isnull', 'join', 'leading', 'limit', 'localtime',
        'localtimestamp', 'not', 'null', 'offset', 'on', 'only', 'or', 'order',
        'placing', 'primary', 'references', 'returning', 'select', 'session_user',
        'some', 'symmetric', 'table', 'then', 'to', 'trailing', 'true', 'union',
        'unique', 'user', 'using', 'when', 'where', 'window', 'with',
    }
    
    VALID_COLUMN_TYPES = {
        # Numeric
        'smallint', 'integer', 'bigint', 'decimal', 'numeric', 'real',
        'double precision', 'smallserial', 'serial', 'bigserial',
        # Monetary
        'money',
        # Character
        'character varying', 'varchar', 'character', 'char', 'text',
        # Binary
        'bytea',
        # Date/Time
        'timestamp', 'timestamp with time zone', 'timestamptz',
        'timestamp without time zone', 'date', 'time', 'time with time zone',
        'time without time zone', 'interval',
        # Boolean
        'boolean', 'bool',
        # UUID
        'uuid',
        # JSON
        'json', 'jsonb',
        # Array (validated separately)
        # Geometric, Network, etc. (advanced types)
    }
    
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.schema: dict[str, Any] = {}
        self.tables: dict[str, dict] = {}
        
    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        try:
            self._load_schema()
            self._validate_structure()
            self._validate_tables()
            self._validate_foreign_keys()
            self._detect_circular_foreign_keys()
            self._check_normalization()
            
            return len(self.errors) == 0
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error: {e}")
            return False
    
    def _load_schema(self) -> None:
        """Load and parse the JSON schema file."""
        with open(self.schema_path, 'r') as f:
            self.schema = json.load(f)
            
        self.tables = self.schema.get('tables', {})
        
    def _validate_structure(self) -> None:
        """Validate top-level schema structure."""
        required_fields = ['name', 'version', 'tables']
        
        for field in required_fields:
            if field not in self.schema:
                self.errors.append(f"Schema missing required field: '{field}'")
        
        if 'description' not in self.schema:
            self.warnings.append("Schema missing 'description' field")
            
    def _validate_tables(self) -> None:
        """Validate individual table definitions."""
        if not self.tables:
            self.errors.append("Schema has no tables defined")
            return
            
        for table_name, table_def in self.tables.items():
            self._validate_table_name(table_name)
            self._validate_table_structure(table_name, table_def)
            self._validate_columns(table_name, table_def.get('columns', {}))
            self._validate_primary_key(table_name, table_def)
            self._validate_indexes(table_name, table_def.get('indexes', []))
    
    def _validate_table_name(self, name: str) -> None:
        """Validate table naming conventions."""
        if not self.TABLE_NAME_PATTERN.match(name):
            self.errors.append(
                f"Table '{name}' violates naming convention "
                "(lowercase letters, numbers, underscores; must start with letter)"
            )
        
        if name.lower() in self.RESERVED_KEYWORDS:
            self.errors.append(
                f"Table '{name}' uses a PostgreSQL reserved keyword"
            )
    
    def _validate_table_structure(self, table_name: str, table_def: dict) -> None:
        """Validate table definition structure."""
        if 'columns' not in table_def:
            self.errors.append(f"Table '{table_name}' has no columns defined")
        
        if not table_def.get('columns'):
            self.errors.append(f"Table '{table_name}' has empty columns list")
            
    def _validate_columns(self, table_name: str, columns: dict) -> None:
        """Validate column definitions."""
        for col_name, col_def in columns.items():
            # Validate column name
            if not self.COLUMN_NAME_PATTERN.match(col_name):
                self.errors.append(
                    f"Column '{table_name}.{col_name}' violates naming convention"
                )
            
            if col_name.lower() in self.RESERVED_KEYWORDS:
                self.warnings.append(
                    f"Column '{table_name}.{col_name}' uses a reserved keyword "
                    "(consider renaming)"
                )
            
            # Validate column type
            col_type = col_def.get('type', '').lower()
            base_type = col_type.replace('[]', '').split('(')[0].strip()
            
            if base_type and base_type not in self.VALID_COLUMN_TYPES:
                self.warnings.append(
                    f"Column '{table_name}.{col_name}' has unusual type: {col_type}"
                )
            
            # Check for missing type
            if not col_type:
                self.errors.append(
                    f"Column '{table_name}.{col_name}' missing type definition"
                )
    
    def _validate_primary_key(self, table_name: str, table_def: dict) -> None:
        """Ensure every table has a primary key."""
        columns = table_def.get('columns', {})
        primary_key = table_def.get('primary_key')
        
        # Check explicit primary_key field
        if primary_key:
            if isinstance(primary_key, str):
                if primary_key not in columns:
                    self.errors.append(
                        f"Table '{table_name}' primary key '{primary_key}' "
                        "references non-existent column"
                    )
            elif isinstance(primary_key, list):
                for pk_col in primary_key:
                    if pk_col not in columns:
                        self.errors.append(
                            f"Table '{table_name}' composite primary key "
                            f"references non-existent column: '{pk_col}'"
                        )
            return
        
        # Check for primary in column definitions
        has_primary = any(
            col.get('primary_key', False) or col.get('primary', False)
            for col in columns.values()
        )
        
        if not has_primary:
            self.errors.append(
                f"Table '{table_name}' has no primary key defined"
            )
    
    def _validate_indexes(self, table_name: str, indexes: list) -> None:
        """Validate index definitions."""
        columns = self.tables.get(table_name, {}).get('columns', {})
        
        for idx in indexes:
            idx_columns = idx.get('columns', [])
            for col in idx_columns:
                if col not in columns:
                    self.errors.append(
                        f"Table '{table_name}' index references "
                        f"non-existent column: '{col}'"
                    )
    
    def _validate_foreign_keys(self) -> None:
        """Validate foreign key references."""
        for table_name, table_def in self.tables.items():
            foreign_keys = table_def.get('foreign_keys', [])
            columns = table_def.get('columns', {})
            
            for fk in foreign_keys:
                # Validate source column exists
                source_col = fk.get('column')
                if source_col and source_col not in columns:
                    self.errors.append(
                        f"Table '{table_name}' foreign key references "
                        f"non-existent local column: '{source_col}'"
                    )
                
                # Validate target table exists
                ref_table = fk.get('references', {}).get('table')
                if ref_table and ref_table not in self.tables:
                    self.errors.append(
                        f"Table '{table_name}' foreign key references "
                        f"non-existent table: '{ref_table}'"
                    )
                
                # Validate target column exists
                ref_col = fk.get('references', {}).get('column')
                if ref_table and ref_col:
                    ref_table_cols = self.tables.get(ref_table, {}).get('columns', {})
                    if ref_col not in ref_table_cols:
                        self.errors.append(
                            f"Table '{table_name}' foreign key references "
                            f"non-existent column: '{ref_table}.{ref_col}'"
                        )
    
    def _detect_circular_foreign_keys(self) -> None:
        """Detect circular foreign key references."""
        # Build dependency graph
        graph: dict[str, set[str]] = {name: set() for name in self.tables}
        
        for table_name, table_def in self.tables.items():
            for fk in table_def.get('foreign_keys', []):
                ref_table = fk.get('references', {}).get('table')
                if ref_table and ref_table in self.tables:
                    graph[table_name].add(ref_table)
        
        # Detect cycles using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in graph}
        
        def find_cycle(node: str, path: list[str]) -> list[str] | None:
            if color[node] == GRAY:
                return path + [node]
            if color[node] == BLACK:
                return None
            
            color[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                cycle = find_cycle(neighbor, path)
                if cycle:
                    return cycle
            
            path.pop()
            color[node] = BLACK
            return None
        
        for node in graph:
            if color[node] == WHITE:
                cycle = find_cycle(node, [])
                if cycle:
                    cycle_path = ' -> '.join(cycle)
                    self.errors.append(
                        f"Circular foreign key dependency detected: {cycle_path}"
                    )
                    break  # Report first cycle only
    
    def _check_normalization(self) -> None:
        """Check for common normalization issues."""
        for table_name, table_def in self.tables.items():
            columns = table_def.get('columns', {})
            
            # Check for repeated column patterns (potential 1NF violation)
            col_names = list(columns.keys())
            numbered_pattern = re.compile(r'^(.+?)_?(\d+)$')
            
            base_names: dict[str, list[str]] = {}
            for col in col_names:
                match = numbered_pattern.match(col)
                if match:
                    base = match.group(1)
                    base_names.setdefault(base, []).append(col)
            
            for base, cols in base_names.items():
                if len(cols) >= 3:
                    self.warnings.append(
                        f"Table '{table_name}' has repeating columns "
                        f"({', '.join(cols[:3])}...) - potential 1NF violation. "
                        "Consider a separate table."
                    )
            
            # Check for potential transitive dependencies (3NF)
            # This is a heuristic based on column naming patterns
            non_pk_cols = [
                col for col, defn in columns.items()
                if not defn.get('primary_key') and not defn.get('primary')
            ]
            
            # Look for "derived" column patterns
            for col in non_pk_cols:
                if '_total' in col or '_sum' in col or '_avg' in col:
                    self.warnings.append(
                        f"Column '{table_name}.{col}' appears to be derived data. "
                        "Consider computing at query time for 3NF compliance."
                    )
    
    def get_report(self) -> str:
        """Generate a validation report."""
        lines = [
            "=" * 60,
            "POSTGRESQL SCHEMA VALIDATION REPORT",
            "=" * 60,
            f"Schema: {self.schema.get('name', 'Unknown')}",
            f"Version: {self.schema.get('version', 'Unknown')}",
            f"Path: {self.schema_path}",
            f"Tables: {len(self.tables)}",
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
            lines.append("✅ Schema validation passed with no issues!")
        elif not self.errors:
            lines.append("✅ Schema is valid (with warnings)")
        else:
            lines.append("❌ Schema validation FAILED")
            
        lines.append("=" * 60)
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Validate PostgreSQL schema definitions'
    )
    parser.add_argument(
        'schema_path',
        type=str,
        help='Path to schema JSON file'
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
    
    schema_path = Path(args.schema_path)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
        
    validator = PostgresSchemaValidator(schema_path)
    is_valid = validator.validate()
    
    if args.strict and validator.warnings:
        is_valid = False
    
    if args.json:
        result = {
            'valid': is_valid,
            'schema': validator.schema.get('name', 'Unknown'),
            'version': validator.schema.get('version', 'Unknown'),
            'table_count': len(validator.tables),
            'errors': validator.errors,
            'warnings': validator.warnings,
        }
        print(json.dumps(result, indent=2))
    else:
        print(validator.get_report())
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
