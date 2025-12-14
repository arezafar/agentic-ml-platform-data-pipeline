#!/usr/bin/env python3
"""
PostgreSQL DDL Generator

Converts validated JSON schema definitions to PostgreSQL 15+ DDL including:
- Table creation with proper types
- JSONB column support
- Declarative partitioning for time-series tables
- Primary and foreign key constraints
- Index generation
- Schema namespace support

Usage:
    python generate_ddl.py <schema.json>
    python generate_ddl.py <schema.json> --output <output.sql>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class DDLGenerator:
    """Generates PostgreSQL 15+ DDL from JSON schema definitions."""
    
    # Type mappings from generic types to PostgreSQL
    TYPE_MAPPINGS = {
        'string': 'TEXT',
        'str': 'TEXT',
        'int': 'INTEGER',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'DOUBLE PRECISION',
        'double': 'DOUBLE PRECISION',
        'decimal': 'NUMERIC',
        'bool': 'BOOLEAN',
        'boolean': 'BOOLEAN',
        'date': 'DATE',
        'datetime': 'TIMESTAMP WITH TIME ZONE',
        'timestamp': 'TIMESTAMP WITH TIME ZONE',
        'timestamptz': 'TIMESTAMP WITH TIME ZONE',
        'json': 'JSONB',
        'jsonb': 'JSONB',
        'uuid': 'UUID',
        'binary': 'BYTEA',
        'bytes': 'BYTEA',
    }
    
    def __init__(self, schema: dict[str, Any]):
        self.schema = schema
        self.tables = schema.get('tables', {})
        self.output_lines: list[str] = []
        
    def generate(self) -> str:
        """Generate complete DDL for the schema."""
        self._add_header()
        self._generate_schemas()
        self._generate_extensions()
        self._generate_tables()
        self._generate_indexes()
        self._generate_foreign_keys()
        self._add_footer()
        
        return '\n'.join(self.output_lines)
    
    def _add_header(self) -> None:
        """Add DDL header with metadata."""
        schema_name = self.schema.get('name', 'unknown')
        version = self.schema.get('version', '1.0.0')
        description = self.schema.get('description', '')
        
        self.output_lines.extend([
            "-- =============================================================================",
            f"-- PostgreSQL 15+ DDL",
            f"-- Schema: {schema_name}",
            f"-- Version: {version}",
            f"-- Generated: {datetime.now().isoformat()}",
            "-- =============================================================================",
            "",
            "-- " + description if description else "",
            "",
            "BEGIN;",
            "",
        ])
    
    def _generate_schemas(self) -> None:
        """Generate CREATE SCHEMA statements."""
        namespaces = set()
        
        for table_name, table_def in self.tables.items():
            namespace = table_def.get('schema', 'public')
            namespaces.add(namespace)
        
        for ns in sorted(namespaces):
            if ns != 'public':
                self.output_lines.extend([
                    f"-- Create schema: {ns}",
                    f"CREATE SCHEMA IF NOT EXISTS {ns};",
                    "",
                ])
    
    def _generate_extensions(self) -> None:
        """Generate required PostgreSQL extensions."""
        extensions = self.schema.get('extensions', [])
        
        # Auto-detect needed extensions
        for table_def in self.tables.values():
            for col_def in table_def.get('columns', {}).values():
                col_type = col_def.get('type', '').lower()
                if col_type == 'uuid':
                    if 'uuid-ossp' not in extensions:
                        extensions.append('uuid-ossp')
        
        if extensions:
            self.output_lines.append("-- Required extensions")
            for ext in extensions:
                self.output_lines.append(
                    f'CREATE EXTENSION IF NOT EXISTS "{ext}";'
                )
            self.output_lines.append("")
    
    def _generate_tables(self) -> None:
        """Generate CREATE TABLE statements."""
        # Sort tables by dependencies
        sorted_tables = self._topological_sort_tables()
        
        for table_name in sorted_tables:
            table_def = self.tables[table_name]
            self._generate_table(table_name, table_def)
    
    def _generate_table(self, table_name: str, table_def: dict) -> None:
        """Generate a single CREATE TABLE statement."""
        namespace = table_def.get('schema', 'public')
        full_name = f"{namespace}.{table_name}" if namespace != 'public' else table_name
        
        columns = table_def.get('columns', {})
        primary_key = table_def.get('primary_key')
        partitioning = table_def.get('partitioning')
        
        self.output_lines.append(f"-- Table: {full_name}")
        self.output_lines.append(f"CREATE TABLE IF NOT EXISTS {full_name} (")
        
        col_definitions = []
        pk_columns = []
        
        for col_name, col_def in columns.items():
            col_ddl = self._generate_column(col_name, col_def)
            col_definitions.append(f"    {col_ddl}")
            
            # Track primary key columns from column definitions
            if col_def.get('primary_key') or col_def.get('primary'):
                pk_columns.append(col_name)
        
        # Handle explicit primary key
        if primary_key:
            if isinstance(primary_key, str):
                pk_columns = [primary_key]
            elif isinstance(primary_key, list):
                pk_columns = primary_key
        
        # Add primary key constraint
        if pk_columns:
            pk_constraint = f"    CONSTRAINT {table_name}_pkey PRIMARY KEY ({', '.join(pk_columns)})"
            col_definitions.append(pk_constraint)
        
        # Add unique constraints
        for unique in table_def.get('unique_constraints', []):
            cols = unique.get('columns', [])
            name = unique.get('name', f"{table_name}_{'_'.join(cols)}_unique")
            col_definitions.append(
                f"    CONSTRAINT {name} UNIQUE ({', '.join(cols)})"
            )
        
        # Add check constraints
        for check in table_def.get('check_constraints', []):
            name = check.get('name', f"{table_name}_check")
            expression = check.get('expression')
            if expression:
                col_definitions.append(
                    f"    CONSTRAINT {name} CHECK ({expression})"
                )
        
        self.output_lines.append(',\n'.join(col_definitions))
        
        # Handle partitioning
        if partitioning:
            partition_type = partitioning.get('type', 'RANGE')
            partition_cols = partitioning.get('columns', [])
            self.output_lines.append(
                f") PARTITION BY {partition_type} ({', '.join(partition_cols)});"
            )
            self._generate_partitions(full_name, partitioning)
        else:
            self.output_lines.append(");")
        
        self.output_lines.append("")
        
        # Add comments
        description = table_def.get('description')
        if description:
            self.output_lines.append(
                f"COMMENT ON TABLE {full_name} IS '{self._escape_string(description)}';"
            )
            self.output_lines.append("")
    
    def _generate_column(self, name: str, definition: dict) -> str:
        """Generate column definition."""
        parts = [name]
        
        # Type
        col_type = definition.get('type', 'TEXT')
        pg_type = self.TYPE_MAPPINGS.get(col_type.lower(), col_type.upper())
        
        # Handle length/precision
        length = definition.get('length')
        precision = definition.get('precision')
        scale = definition.get('scale')
        
        if precision and scale:
            pg_type = f"{pg_type}({precision}, {scale})"
        elif length:
            if pg_type in ('TEXT', 'VARCHAR', 'CHARACTER VARYING'):
                pg_type = f"VARCHAR({length})"
        
        # Handle arrays
        if definition.get('array'):
            pg_type = f"{pg_type}[]"
        
        parts.append(pg_type)
        
        # NOT NULL
        if definition.get('not_null') or definition.get('required'):
            parts.append("NOT NULL")
        
        # DEFAULT
        default = definition.get('default')
        if default is not None:
            if isinstance(default, str):
                if default.upper() in ('NOW()', 'CURRENT_TIMESTAMP', 'GEN_RANDOM_UUID()'):
                    parts.append(f"DEFAULT {default}")
                else:
                    parts.append(f"DEFAULT '{self._escape_string(default)}'")
            elif isinstance(default, bool):
                parts.append(f"DEFAULT {str(default).upper()}")
            else:
                parts.append(f"DEFAULT {default}")
        
        # GENERATED
        generated = definition.get('generated')
        if generated:
            parts.append(f"GENERATED ALWAYS AS ({generated}) STORED")
        
        return ' '.join(parts)
    
    def _generate_partitions(self, table_name: str, partitioning: dict) -> None:
        """Generate partition tables for partitioned table."""
        partition_type = partitioning.get('type', 'RANGE')
        
        if partition_type == 'RANGE':
            # Generate time-based partitions
            partitions = partitioning.get('partitions', [])
            for partition in partitions:
                name = partition.get('name')
                from_val = partition.get('from')
                to_val = partition.get('to')
                
                if name and from_val and to_val:
                    self.output_lines.append(
                        f"CREATE TABLE IF NOT EXISTS {table_name}_{name} "
                        f"PARTITION OF {table_name} "
                        f"FOR VALUES FROM ('{from_val}') TO ('{to_val}');"
                    )
            
            # Add default partition
            if partitioning.get('default_partition', True):
                self.output_lines.append(
                    f"CREATE TABLE IF NOT EXISTS {table_name}_default "
                    f"PARTITION OF {table_name} DEFAULT;"
                )
        
        self.output_lines.append("")
    
    def _generate_indexes(self) -> None:
        """Generate CREATE INDEX statements."""
        for table_name, table_def in self.tables.items():
            namespace = table_def.get('schema', 'public')
            full_name = f"{namespace}.{table_name}" if namespace != 'public' else table_name
            
            indexes = table_def.get('indexes', [])
            
            for idx in indexes:
                idx_name = idx.get('name', f"idx_{table_name}_{'_'.join(idx.get('columns', []))}")
                idx_type = idx.get('type', 'btree').upper()
                columns = idx.get('columns', [])
                unique = idx.get('unique', False)
                where = idx.get('where')
                
                if not columns:
                    continue
                
                unique_str = "UNIQUE " if unique else ""
                using_str = f" USING {idx_type}" if idx_type != 'BTREE' else ""
                where_str = f" WHERE {where}" if where else ""
                
                self.output_lines.append(
                    f"CREATE {unique_str}INDEX IF NOT EXISTS {idx_name} "
                    f"ON {full_name}{using_str} ({', '.join(columns)}){where_str};"
                )
            
            # Auto-create JSONB GIN indexes
            for col_name, col_def in table_def.get('columns', {}).items():
                col_type = col_def.get('type', '').lower()
                if col_type in ('json', 'jsonb') and col_def.get('index', True):
                    self.output_lines.append(
                        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{col_name}_gin "
                        f"ON {full_name} USING GIN ({col_name});"
                    )
        
        if self.output_lines[-1] != "":
            self.output_lines.append("")
    
    def _generate_foreign_keys(self) -> None:
        """Generate ALTER TABLE statements for foreign keys."""
        for table_name, table_def in self.tables.items():
            namespace = table_def.get('schema', 'public')
            full_name = f"{namespace}.{table_name}" if namespace != 'public' else table_name
            
            foreign_keys = table_def.get('foreign_keys', [])
            
            for fk in foreign_keys:
                col = fk.get('column')
                ref = fk.get('references', {})
                ref_table = ref.get('table')
                ref_col = ref.get('column', 'id')
                
                if not col or not ref_table:
                    continue
                
                fk_name = fk.get('name', f"fk_{table_name}_{col}")
                on_delete = fk.get('on_delete', 'NO ACTION')
                on_update = fk.get('on_update', 'NO ACTION')
                
                # Handle schema prefix for referenced table
                ref_full_name = ref_table
                if '.' not in ref_table and namespace != 'public':
                    ref_full_name = f"{namespace}.{ref_table}"
                
                self.output_lines.append(
                    f"ALTER TABLE {full_name} ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY ({col}) REFERENCES {ref_full_name}({ref_col}) "
                    f"ON DELETE {on_delete} ON UPDATE {on_update};"
                )
        
        if self.output_lines[-1] != "":
            self.output_lines.append("")
    
    def _add_footer(self) -> None:
        """Add DDL footer."""
        self.output_lines.extend([
            "COMMIT;",
            "",
            "-- =============================================================================",
            "-- End of DDL",
            "-- =============================================================================",
        ])
    
    def _topological_sort_tables(self) -> list[str]:
        """Sort tables by foreign key dependencies."""
        # Build dependency graph
        deps: dict[str, set[str]] = {name: set() for name in self.tables}
        
        for table_name, table_def in self.tables.items():
            for fk in table_def.get('foreign_keys', []):
                ref_table = fk.get('references', {}).get('table')
                if ref_table and ref_table in self.tables and ref_table != table_name:
                    deps[table_name].add(ref_table)
        
        # Kahn's algorithm for topological sort
        result = []
        no_deps = [t for t, d in deps.items() if not d]
        
        while no_deps:
            node = no_deps.pop(0)
            result.append(node)
            
            for table in list(deps.keys()):
                if node in deps[table]:
                    deps[table].remove(node)
                    if not deps[table]:
                        no_deps.append(table)
        
        # Add any remaining tables (circular deps)
        for table in self.tables:
            if table not in result:
                result.append(table)
        
        return result
    
    def _escape_string(self, value: str) -> str:
        """Escape single quotes in string values."""
        return value.replace("'", "''")


def main():
    parser = argparse.ArgumentParser(
        description='Generate PostgreSQL DDL from JSON schema'
    )
    parser.add_argument(
        'schema_path',
        type=str,
        help='Path to schema JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output SQL file path (default: stdout)'
    )
    
    args = parser.parse_args()
    
    schema_path = Path(args.schema_path)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    generator = DDLGenerator(schema)
    ddl = generator.generate()
    
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            f.write(ddl)
        print(f"DDL written to: {output_path}")
    else:
        print(ddl)


if __name__ == '__main__':
    main()
