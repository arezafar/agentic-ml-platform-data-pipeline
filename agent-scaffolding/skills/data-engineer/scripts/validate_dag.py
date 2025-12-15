#!/usr/bin/env python3
"""
Airflow DAG Validator

Parses Python files to validate Airflow DAG objects including:
- DAG object instantiation
- Task dependencies
- Start dates and schedule intervals
- Operator configurations
- Best practices compliance

Usage:
    python validate_dag.py <dag_file.py>
    python validate_dag.py <directory> --recursive
"""

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class DAGValidationError(Exception):
    """Custom exception for DAG validation errors."""
    pass


class AirflowDAGValidator(ast.NodeVisitor):
    """AST-based validator for Airflow DAG files."""
    
    # Known Airflow operators
    KNOWN_OPERATORS = {
        'PythonOperator', 'BashOperator', 'DummyOperator', 'EmptyOperator',
        'BranchPythonOperator', 'ShortCircuitOperator',
        'PostgresOperator', 'MySqlOperator', 'MsSqlOperator',
        'S3ToRedshiftOperator', 'RedshiftToS3Operator',
        'EmailOperator', 'SlackOperator',
        'DockerOperator', 'KubernetesPodOperator',
        'HttpOperator', 'SimpleHttpOperator',
        'TriggerDagRunOperator', 'ExternalTaskSensor',
        'SqlSensor', 'S3KeySensor', 'FileSensor',
        'PythonSensor', 'TimeDeltaSensor',
    }
    
    # Required DAG args
    REQUIRED_DAG_ARGS = {'dag_id'}
    RECOMMENDED_DAG_ARGS = {'start_date', 'schedule_interval', 'catchup'}
    
    def __init__(self, filepath: str, source_code: str):
        self.filepath = filepath
        self.source_code = source_code
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.info: list[dict[str, Any]] = []
        
        self.dags: list[dict[str, Any]] = []
        self.tasks: dict[str, dict[str, Any]] = {}
        self.dependencies: list[tuple[str, str]] = []
        self.imports: set[str] = set()
        
    def validate(self) -> bool:
        """Run all validation checks. Returns True if no errors."""
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
            
            self._validate_dag_presence()
            self._validate_dag_configurations()
            self._validate_task_ids()
            self._validate_operator_usage()
            self._check_best_practices()
            
            return len(self.errors) == 0
        except SyntaxError as e:
            self.errors.append({
                'line': e.lineno or 0,
                'code': 'E001',
                'message': f'Syntax error: {e.msg}',
            })
            return False
    
    def visit_Import(self, node: ast.Import) -> None:
        """Track imports."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports."""
        module = node.module or ''
        for alias in node.names:
            self.imports.add(f"{module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Detect DAG and operator instantiations."""
        func_name = self._get_call_name(node)
        
        if func_name == 'DAG':
            self._extract_dag_info(node)
        elif func_name in self.KNOWN_OPERATORS or func_name.endswith('Operator') or func_name.endswith('Sensor'):
            self._extract_task_info(node, func_name)
        
        self.generic_visit(node)
    
    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Detect task dependencies via >> and << operators."""
        if isinstance(node.op, ast.RShift):  # >>
            left_name = self._get_node_name(node.left)
            right_name = self._get_node_name(node.right)
            if left_name and right_name:
                self.dependencies.append((left_name, right_name))
        elif isinstance(node.op, ast.LShift):  # <<
            left_name = self._get_node_name(node.left)
            right_name = self._get_node_name(node.right)
            if left_name and right_name:
                self.dependencies.append((right_name, left_name))
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the function/class name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ''
    
    def _get_node_name(self, node: ast.AST) -> Optional[str]:
        """Extract variable name from a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            # Inline operator definition
            return self._extract_task_id_from_call(node)
        return None
    
    def _extract_dag_info(self, node: ast.Call) -> None:
        """Extract DAG configuration from DAG() call."""
        dag_info = {
            'line': node.lineno,
            'dag_id': None,
            'start_date': None,
            'schedule_interval': None,
            'catchup': None,
            'default_args': {},
        }
        
        # Positional args
        if node.args and isinstance(node.args[0], ast.Constant):
            dag_info['dag_id'] = node.args[0].value
        
        # Keyword args
        for kw in node.keywords:
            if kw.arg == 'dag_id' and isinstance(kw.value, ast.Constant):
                dag_info['dag_id'] = kw.value.value
            elif kw.arg == 'start_date':
                dag_info['start_date'] = self._extract_date(kw.value)
            elif kw.arg == 'schedule_interval':
                dag_info['schedule_interval'] = self._extract_schedule(kw.value)
            elif kw.arg == 'catchup' and isinstance(kw.value, ast.Constant):
                dag_info['catchup'] = kw.value.value
            elif kw.arg == 'default_args':
                dag_info['default_args'] = self._extract_dict(kw.value)
        
        self.dags.append(dag_info)
    
    def _extract_task_info(self, node: ast.Call, operator: str) -> None:
        """Extract task information from operator instantiation."""
        task_info = {
            'line': node.lineno,
            'operator': operator,
            'task_id': None,
            'retries': None,
            'retry_delay': None,
        }
        
        for kw in node.keywords:
            if kw.arg == 'task_id' and isinstance(kw.value, ast.Constant):
                task_info['task_id'] = kw.value.value
            elif kw.arg == 'retries' and isinstance(kw.value, ast.Constant):
                task_info['retries'] = kw.value.value
        
        if task_info['task_id']:
            self.tasks[task_info['task_id']] = task_info
    
    def _extract_task_id_from_call(self, node: ast.Call) -> Optional[str]:
        """Extract task_id from an inline operator call."""
        for kw in node.keywords:
            if kw.arg == 'task_id' and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None
    
    def _extract_date(self, node: ast.AST) -> Optional[str]:
        """Extract date representation from AST node."""
        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            if func_name in ('datetime', 'date'):
                args = [a.value for a in node.args if isinstance(a, ast.Constant)]
                if len(args) >= 3:
                    return f"{args[0]}-{args[1]:02d}-{args[2]:02d}"
            elif func_name == 'days_ago':
                if node.args and isinstance(node.args[0], ast.Constant):
                    return f"days_ago({node.args[0].value})"
        return 'dynamic'
    
    def _extract_schedule(self, node: ast.AST) -> Optional[str]:
        """Extract schedule interval from AST node."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id  # e.g., None
        return 'dynamic'
    
    def _extract_dict(self, node: ast.AST) -> dict:
        """Extract dictionary from AST node."""
        result = {}
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
                    result[key.value] = value.value
        return result
    
    def _validate_dag_presence(self) -> None:
        """Ensure at least one DAG is defined."""
        if not self.dags:
            self.errors.append({
                'line': 1,
                'code': 'E002',
                'message': 'No DAG object found in file',
            })
    
    def _validate_dag_configurations(self) -> None:
        """Validate each DAG's configuration."""
        for dag in self.dags:
            # Check required args
            if not dag['dag_id']:
                self.errors.append({
                    'line': dag['line'],
                    'code': 'E003',
                    'message': 'DAG missing required argument: dag_id',
                })
            
            # Check recommended args
            if dag['start_date'] is None:
                self.warnings.append({
                    'line': dag['line'],
                    'code': 'W001',
                    'message': 'DAG missing recommended argument: start_date',
                })
            
            if dag['schedule_interval'] is None:
                self.warnings.append({
                    'line': dag['line'],
                    'code': 'W002',
                    'message': 'DAG missing schedule_interval (will run on manual trigger only)',
                })
            
            if dag['catchup'] is None:
                self.info.append({
                    'line': dag['line'],
                    'code': 'I001',
                    'message': 'Consider setting catchup=False to prevent backfilling',
                })
    
    def _validate_task_ids(self) -> None:
        """Validate task ID uniqueness and format."""
        task_ids = list(self.tasks.keys())
        
        # Check for duplicates
        seen = set()
        for tid in task_ids:
            if tid in seen:
                self.errors.append({
                    'line': self.tasks[tid]['line'],
                    'code': 'E004',
                    'message': f"Duplicate task_id: '{tid}'",
                })
            seen.add(tid)
        
        # Check format (lowercase, underscores)
        pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        for tid, info in self.tasks.items():
            if not pattern.match(tid):
                self.warnings.append({
                    'line': info['line'],
                    'code': 'W003',
                    'message': f"Task ID '{tid}' doesn't follow naming convention (lowercase_snake_case)",
                })
    
    def _validate_operator_usage(self) -> None:
        """Validate operator configurations."""
        for task_id, info in self.tasks.items():
            # Check for retries
            if info['retries'] is None:
                self.info.append({
                    'line': info['line'],
                    'code': 'I002',
                    'message': f"Task '{task_id}' has no retries configured",
                })
    
    def _check_best_practices(self) -> None:
        """Check for Airflow best practices."""
        # Check for Airflow imports
        has_airflow_import = any('airflow' in imp for imp in self.imports)
        if not has_airflow_import:
            self.warnings.append({
                'line': 1,
                'code': 'W004',
                'message': 'No Airflow imports detected',
            })
        
        # Check for tasks without dependencies
        all_task_ids = set(self.tasks.keys())
        tasks_with_deps = set()
        for left, right in self.dependencies:
            tasks_with_deps.add(left)
            tasks_with_deps.add(right)
        
        orphan_tasks = all_task_ids - tasks_with_deps
        for tid in orphan_tasks:
            self.warnings.append({
                'line': self.tasks[tid]['line'],
                'code': 'W005',
                'message': f"Task '{tid}' has no dependencies (orphan task)",
            })
    
    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Build adjacency list from dependencies."""
        graph: dict[str, list[str]] = {tid: [] for tid in self.tasks}
        for left, right in self.dependencies:
            if left in graph:
                graph[left].append(right)
        return graph
    
    def get_report(self) -> str:
        """Generate validation report."""
        lines = [
            "=" * 60,
            "AIRFLOW DAG VALIDATION REPORT",
            "=" * 60,
            f"File: {self.filepath}",
            f"DAGs found: {len(self.dags)}",
            f"Tasks found: {len(self.tasks)}",
            f"Dependencies: {len(self.dependencies)}",
            "",
        ]
        
        if self.dags:
            lines.append("DAG CONFIGURATIONS:")
            for dag in self.dags:
                lines.append(f"  - {dag['dag_id']} (schedule: {dag['schedule_interval']})")
            lines.append("")
        
        if self.tasks:
            lines.append("TASKS:")
            for tid, info in self.tasks.items():
                lines.append(f"  - {tid} ({info['operator']})")
            lines.append("")
        
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ❌ Line {err['line']}: [{err['code']}] {err['message']}")
            lines.append("")
        
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ⚠️  Line {warn['line']}: [{warn['code']}] {warn['message']}")
            lines.append("")
        
        if self.info:
            lines.append(f"INFO ({len(self.info)}):")
            for inf in self.info:
                lines.append(f"  ℹ️  Line {inf['line']}: [{inf['code']}] {inf['message']}")
            lines.append("")
        
        if not self.errors:
            lines.append("✅ DAG validation passed!")
        else:
            lines.append("❌ DAG validation FAILED")
        
        lines.append("=" * 60)
        return '\n'.join(lines)


def validate_file(filepath: Path) -> tuple[bool, AirflowDAGValidator]:
    """Validate a single DAG file."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    validator = AirflowDAGValidator(str(filepath), source)
    is_valid = validator.validate()
    return is_valid, validator


def main():
    parser = argparse.ArgumentParser(description='Validate Airflow DAG files')
    parser.add_argument('path', type=str, help='Path to DAG file or directory')
    parser.add_argument('--recursive', '-r', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true')
    
    args = parser.parse_args()
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_file():
        is_valid, validator = validate_file(path)
        validators = [validator]
    else:
        pattern = '**/*.py' if args.recursive else '*.py'
        validators = []
        is_valid = True
        for filepath in path.glob(pattern):
            valid, val = validate_file(filepath)
            if not valid:
                is_valid = False
            if val.dags:
                validators.append(val)
    
    if args.strict:
        for v in validators:
            if v.warnings:
                is_valid = False
    
    if args.json:
        results = [{
            'file': v.filepath,
            'dags': v.dags,
            'tasks': list(v.tasks.keys()),
            'dependencies': v.dependencies,
            'errors': v.errors,
            'warnings': v.warnings,
        } for v in validators]
        print(json.dumps({'valid': is_valid, 'results': results}, indent=2))
    else:
        for v in validators:
            print(v.get_report())
            print()
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
