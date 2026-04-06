from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List, Set, Tuple


@dataclass
class Issue:
    type: str
    name: str
    line: int
    message: str


@dataclass
class CheckResults:
    unused_imports: List[Issue] = field(default_factory=list)
    unused_variables: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (
            len(self.unused_imports)
            + len(self.unused_variables)
            + len(self.long_functions)
            + len(self.deep_nesting)
        )


class _NameCollector(ast.NodeVisitor):
    """Collect all Name nodes that are referenced (loaded)."""

    def __init__(self):
        self.used_names: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if not isinstance(node.ctx, ast.Store):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


class _ImportCollector(ast.NodeVisitor):
    """Collect all import statements with their local binding names."""

    def __init__(self):
        self.imports: List[Tuple[str, str, int]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.imports.append((local_name, alias.name, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.append((local_name, full_name, node.lineno))


class _AssignmentCollector(ast.NodeVisitor):
    """Collect variable assignments inside functions."""

    def __init__(self):
        self.assignments: List[Tuple[str, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_from_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_from_function(node)

    def _collect_from_function(self, func_node: ast.AST) -> None:
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.assignments.append((target.id, node.lineno))
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    self.assignments.append((node.target.id, node.lineno))


class _FunctionLengthChecker(ast.NodeVisitor):
    """Detect functions longer than a given threshold."""

    def __init__(self, max_lines: int = 50):
        self.max_lines = max_lines
        self.long_functions: List[Tuple[str, int, int, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def _check(self, node: ast.AST) -> None:
        if not hasattr(node, "body") or not node.body:
            return
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", None) or start_line
        length = end_line - start_line + 1
        if length > self.max_lines:
            self.long_functions.append((node.name, start_line, end_line, length))


class _NestingChecker:
    """Detect nesting deeper than a given threshold inside functions."""

    NESTING_TYPES = (ast.If, ast.For, ast.While, ast.With, ast.Try)

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.issues: List[Tuple[str, int, int]] = []

    def check(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._walk_nesting(node, node.name, 0)

    def _walk_nesting(self, node: ast.AST, func_name: str, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(child, self.NESTING_TYPES):
                new_depth = depth + 1
                if new_depth > self.max_depth:
                    self.issues.append((func_name, child.lineno, new_depth))
                self._walk_nesting(child, func_name, new_depth)
            else:
                self._walk_nesting(child, func_name, depth)


def check_code(source: str) -> CheckResults:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python source: {e}") from e

    results = CheckResults()

    # --- Unused imports ---
    name_collector = _NameCollector()
    name_collector.visit(tree)
    used_names = name_collector.used_names

    import_collector = _ImportCollector()
    import_collector.visit(tree)

    import_local_names: Set[str] = set()
    for local_name, full_name, lineno in import_collector.imports:
        import_local_names.add(local_name)
        top_level = local_name.split(".")[0]
        if local_name not in used_names and top_level not in used_names:
            results.unused_imports.append(
                Issue(
                    type="unused_import",
                    name=full_name,
                    line=lineno,
                    message=f"'{full_name}' imported but never used",
                )
            )

    # --- Unused variables ---
    assign_collector = _AssignmentCollector()
    assign_collector.visit(tree)

    all_reads: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
            all_reads.add(node.id)

    reported_vars: Set[str] = set()
    for var_name, lineno in assign_collector.assignments:
        if var_name.startswith("_"):
            continue
        if var_name in import_local_names:
            continue
        if var_name not in all_reads and var_name not in reported_vars:
            results.unused_variables.append(
                Issue(
                    type="unused_variable",
                    name=var_name,
                    line=lineno,
                    message=f"Variable '{var_name}' assigned but never read",
                )
            )
            reported_vars.add(var_name)

    # --- Long functions ---
    func_checker = _FunctionLengthChecker(max_lines=50)
    func_checker.visit(tree)
    for name, start, end, length in func_checker.long_functions:
        results.long_functions.append(
            Issue(
                type="long_function",
                name=name,
                line=start,
                message=f"Function '{name}' is {length} lines long (limit is 50)",
            )
        )

    # --- Deep nesting ---
    nesting_checker = _NestingChecker(max_depth=4)
    nesting_checker.check(tree)
    for func_name, lineno, depth in nesting_checker.issues:
        results.deep_nesting.append(
            Issue(
                type="deep_nesting",
                name=func_name,
                line=lineno,
                message=f"Nesting depth {depth} in '{func_name}' exceeds maximum of 4",
            )
        )

    return results


if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json

def process_data(items):
    result = []
    unused_var = 42
    for item in items:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    for x in range(sub):
                        if x > 0:
                            for y in range(x):
                                result.append(y)
    return result

def short_func():
    return 1
'''

    results = check_code(sample_code)
    print(f"Total issues found: {results.total_issues}")

    print(f"\nUnused imports ({len(results.unused_imports)}):")
    for issue in results.unused_imports:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nUnused variables ({len(results.unused_variables)}):")
    for issue in results.unused_variables:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nLong functions ({len(results.long_functions)}):")
    for issue in results.long_functions:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nDeep nesting ({len(results.deep_nesting)}):")
    for issue in results.deep_nesting:
        print(f"  Line {issue.line}: {issue.message}")
