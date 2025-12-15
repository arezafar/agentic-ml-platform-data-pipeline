#!/usr/bin/env python3
"""
Cyclic Dependency Detector

Algorithmically detects circular dependencies in DAGs using:
- DFS-based cycle detection
- Tarjan's algorithm for strongly connected components
- Visual cycle path reporting

Usage:
    python check_cyclic_dependencies.py <dag_file.py>
    python check_cyclic_dependencies.py --graph '{"a": ["b"], "b": ["c"], "c": ["a"]}'
    python check_cyclic_dependencies.py --test
"""

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional


class CyclicDependencyError(Exception):
    """Raised when a cycle is detected."""
    pass


class DependencyGraph:
    """Graph representation for dependency analysis."""
    
    def __init__(self):
        self.graph: dict[str, list[str]] = defaultdict(list)
        self.nodes: set[str] = set()
    
    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source to target."""
        self.nodes.add(source)
        self.nodes.add(target)
        self.graph[source].append(target)
    
    def add_node(self, node: str) -> None:
        """Add a node without edges."""
        self.nodes.add(node)
        if node not in self.graph:
            self.graph[node] = []
    
    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> 'DependencyGraph':
        """Create graph from adjacency list dictionary."""
        graph = cls()
        for source, targets in data.items():
            graph.add_node(source)
            for target in targets:
                graph.add_edge(source, target)
        return graph
    
    def detect_cycle_dfs(self) -> tuple[bool, Optional[list[str]]]:
        """Detect cycles using DFS coloring.
        
        Returns:
            Tuple of (has_cycle, cycle_path)
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.nodes}
        parent = {node: None for node in self.nodes}
        
        def dfs(node: str, path: list[str]) -> Optional[list[str]]:
            color[node] = GRAY
            path.append(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in color:
                    color[neighbor] = WHITE
                    parent[neighbor] = node
                
                if color[neighbor] == GRAY:
                    # Found cycle - extract cycle path
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                
                if color[neighbor] == WHITE:
                    result = dfs(neighbor, path)
                    if result:
                        return result
            
            path.pop()
            color[node] = BLACK
            return None
        
        for node in self.nodes:
            if color[node] == WHITE:
                cycle = dfs(node, [])
                if cycle:
                    return True, cycle
        
        return False, None
    
    def find_all_cycles(self) -> list[list[str]]:
        """Find all cycles using Johnson's algorithm variant.
        
        Returns:
            List of cycles (each cycle is a list of nodes)
        """
        cycles = []
        
        def find_cycles_from(start: str) -> None:
            stack = [(start, [start], set([start]))]
            
            while stack:
                node, path, visited = stack.pop()
                
                for neighbor in self.graph.get(node, []):
                    if neighbor == start and len(path) > 1:
                        cycles.append(path + [start])
                    elif neighbor not in visited:
                        stack.append((neighbor, path + [neighbor], visited | {neighbor}))
        
        for node in self.nodes:
            find_cycles_from(node)
        
        # Remove duplicate cycles
        unique_cycles = []
        seen = set()
        for cycle in cycles:
            # Normalize cycle for comparison
            min_idx = cycle.index(min(cycle[:-1]))  # Exclude last (duplicate of first)
            normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx])
            if normalized not in seen:
                seen.add(normalized)
                unique_cycles.append(cycle)
        
        return unique_cycles
    
    def topological_sort(self) -> tuple[bool, list[str]]:
        """Perform topological sort using Kahn's algorithm.
        
        Returns:
            Tuple of (success, sorted_nodes or empty list if cycle)
        """
        in_degree = {node: 0 for node in self.nodes}
        
        for source in self.graph:
            for target in self.graph[source]:
                in_degree[target] = in_degree.get(target, 0) + 1
        
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) == len(self.nodes):
            return True, result
        else:
            return False, []
    
    def get_strongly_connected_components(self) -> list[list[str]]:
        """Find SCCs using Tarjan's algorithm.
        
        Returns:
            List of strongly connected components
        """
        index_counter = [0]
        stack = []
        lowlink = {}
        index = {}
        on_stack = {}
        sccs = []
        
        def strongconnect(node: str) -> None:
            index[node] = index_counter[0]
            lowlink[node] = index_counter[0]
            index_counter[0] += 1
            on_stack[node] = True
            stack.append(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink[neighbor])
                elif on_stack.get(neighbor, False):
                    lowlink[node] = min(lowlink[node], index[neighbor])
            
            if lowlink[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1 or (len(scc) == 1 and node in self.graph.get(node, [])):
                    sccs.append(scc)
        
        for node in self.nodes:
            if node not in index:
                strongconnect(node)
        
        return sccs


class DAGDependencyExtractor(ast.NodeVisitor):
    """Extract task dependencies from Python DAG files."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.graph = DependencyGraph()
        self.task_vars: dict[str, str] = {}  # variable name -> task_id
    
    def extract(self) -> DependencyGraph:
        """Parse and extract dependencies."""
        tree = ast.parse(self.source_code)
        self.visit(tree)
        return self.graph
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Track task variable assignments."""
        if isinstance(node.value, ast.Call):
            task_id = self._extract_task_id(node.value)
            if task_id:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.task_vars[target.id] = task_id
                        self.graph.add_node(task_id)
        self.generic_visit(node)
    
    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Extract dependencies from >> and << operators."""
        if isinstance(node.op, ast.RShift):  # >>
            lefts = self._get_task_ids(node.left)
            rights = self._get_task_ids(node.right)
            for left in lefts:
                for right in rights:
                    self.graph.add_edge(left, right)
        elif isinstance(node.op, ast.LShift):  # <<
            lefts = self._get_task_ids(node.left)
            rights = self._get_task_ids(node.right)
            for left in lefts:
                for right in rights:
                    self.graph.add_edge(right, left)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Extract dependencies from set_downstream/set_upstream."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'set_downstream':
                source = self._get_task_ids(node.func.value)
                for arg in node.args:
                    targets = self._get_task_ids(arg)
                    for s in source:
                        for t in targets:
                            self.graph.add_edge(s, t)
            elif node.func.attr == 'set_upstream':
                source = self._get_task_ids(node.func.value)
                for arg in node.args:
                    targets = self._get_task_ids(arg)
                    for s in source:
                        for t in targets:
                            self.graph.add_edge(t, s)
        self.generic_visit(node)
    
    def _extract_task_id(self, call_node: ast.Call) -> Optional[str]:
        """Extract task_id from operator call."""
        for kw in call_node.keywords:
            if kw.arg == 'task_id' and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None
    
    def _get_task_ids(self, node: ast.AST) -> list[str]:
        """Get task IDs from a node (variable or list)."""
        if isinstance(node, ast.Name):
            if node.id in self.task_vars:
                return [self.task_vars[node.id]]
            return [node.id]  # Assume variable name is task id
        elif isinstance(node, ast.List):
            result = []
            for elt in node.elts:
                result.extend(self._get_task_ids(elt))
            return result
        elif isinstance(node, ast.Call):
            task_id = self._extract_task_id(node)
            if task_id:
                return [task_id]
        return []


def check_file(filepath: Path) -> tuple[DependencyGraph, bool, list[str]]:
    """Check a DAG file for cycles."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    extractor = DAGDependencyExtractor(source)
    graph = extractor.extract()
    
    has_cycle, cycle = graph.detect_cycle_dfs()
    return graph, has_cycle, cycle or []


def check_graph(graph_dict: dict) -> tuple[DependencyGraph, bool, list[str]]:
    """Check a graph dictionary for cycles."""
    graph = DependencyGraph.from_dict(graph_dict)
    has_cycle, cycle = graph.detect_cycle_dfs()
    return graph, has_cycle, cycle or []


def run_tests() -> bool:
    """Run built-in tests for cycle detection."""
    print("Running cycle detection tests...\n")
    
    tests = [
        # (name, graph, expected_has_cycle)
        ("Simple acyclic", {"a": ["b"], "b": ["c"], "c": []}, False),
        ("Simple cycle", {"a": ["b"], "b": ["c"], "c": ["a"]}, True),
        ("Self loop", {"a": ["a"]}, True),
        ("Diamond (acyclic)", {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}, False),
        ("Complex cycle", {"a": ["b"], "b": ["c", "d"], "c": ["e"], "d": ["e"], "e": ["b"]}, True),
        ("Disconnected acyclic", {"a": ["b"], "b": [], "c": ["d"], "d": []}, False),
        ("Disconnected with cycle", {"a": ["b"], "b": [], "c": ["d"], "d": ["c"]}, True),
    ]
    
    all_passed = True
    for name, graph_dict, expected in tests:
        graph, has_cycle, cycle = check_graph(graph_dict)
        passed = has_cycle == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} {name}")
        if has_cycle:
            print(f"   Cycle: {' -> '.join(cycle)}")
        
        if not passed:
            all_passed = False
            print(f"   Expected: {expected}, Got: {has_cycle}")
        print()
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description='Check for cyclic dependencies in DAGs')
    parser.add_argument('path', nargs='?', type=str, help='Path to DAG file')
    parser.add_argument('--graph', type=str, help='JSON adjacency list to check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--test', action='store_true', help='Run built-in tests')
    parser.add_argument('--all-cycles', action='store_true', help='Find all cycles')
    
    args = parser.parse_args()
    
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)
    
    if args.graph:
        graph_dict = json.loads(args.graph)
        graph, has_cycle, cycle = check_graph(graph_dict)
    elif args.path:
        path = Path(args.path)
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        graph, has_cycle, cycle = check_file(path)
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.all_cycles:
        all_cycles = graph.find_all_cycles()
        if args.json:
            print(json.dumps({
                'has_cycles': len(all_cycles) > 0,
                'cycle_count': len(all_cycles),
                'cycles': all_cycles,
            }, indent=2))
        else:
            if all_cycles:
                print(f"Found {len(all_cycles)} cycle(s):")
                for i, c in enumerate(all_cycles, 1):
                    print(f"  {i}. {' -> '.join(c)}")
            else:
                print("No cycles found.")
        sys.exit(1 if all_cycles else 0)
    
    if args.json:
        print(json.dumps({
            'has_cycle': has_cycle,
            'cycle': cycle,
            'nodes': list(graph.nodes),
            'edges': [(k, v) for k, vs in graph.graph.items() for v in vs],
        }, indent=2))
    else:
        print("=" * 60)
        print("CYCLIC DEPENDENCY CHECK")
        print("=" * 60)
        print(f"Nodes: {len(graph.nodes)}")
        print(f"Edges: {sum(len(v) for v in graph.graph.values())}")
        print()
        
        if has_cycle:
            print("❌ CYCLE DETECTED!")
            print(f"   {' -> '.join(cycle)}")
        else:
            print("✅ No cycles detected")
            
            # Show topological order
            success, order = graph.topological_sort()
            if success:
                print(f"\nTopological order: {' -> '.join(order)}")
        
        print("=" * 60)
    
    sys.exit(1 if has_cycle else 0)


if __name__ == '__main__':
    main()
