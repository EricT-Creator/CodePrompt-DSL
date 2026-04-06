import ast
import sys
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class CheckResults:
    """Results from static code analysis."""
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[str] = field(default_factory=list)
    deep_nesting: List[str] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (
            len(self.unused_imports)
            + len(self.unused_variables)
            + len(self.long_functions)
            + len(self.deep_nesting)
        )

    def __str__(self) -> str:
        lines = ["=== Code Check Results ==="]
        if self.unused_imports:
            lines.append(f"\nUnused Imports ({len(self.unused_imports)}):")
            for item in self.unused_imports:
                lines.append(f"  - {item}")
        if self.unused_variables:
            lines.append(f"\nUnused Variables ({len(self.unused_variables)}):")
            for item in self.unused_variables:
                lines.append(f"  - {item}")
        if self.long_functions:
            lines.append(f"\nLong Functions >50 lines ({len(self.long_functions)}):")
            for item in self.long_functions:
                lines.append(f"  - {item}")
        if self.deep_nesting:
            lines.append(f"\nDeep Nesting >4 levels ({len(self.deep_nesting)}):")
            for item in self.deep_nesting:
                lines.append(f"  - {item}")
        if self.total_issues == 0:
            lines.append("\nNo issues found!")
        else:
            lines.append(f"\nTotal issues: {self.total_issues}")
        return "\n".join(lines)


class ImportCollector(ast.NodeVisitor):
    """Collect all imported names."""

    def __init__(self) -> None:
        self.imported_names: dict = {}  # name -> line number

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)


class NameUsageCollector(ast.NodeVisitor):
    """Collect all Name references (excluding import/store targets)."""

    def __init__(self, imported_names: Set[str]) -> None:
        self.imported_names = imported_names
        self.used_names: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check if the root is an imported module
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            self.used_names.add(root.id)
        self.generic_visit(node)


class VariableCollector(ast.NodeVisitor):
    """Collect variable assignments at function scope and detect unused ones."""

    def __init__(self) -> None:
        self.results: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef) -> None:
        assigned: dict = {}  # name -> line
        used: Set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in assigned and not child.id.startswith("_"):
                        assigned[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    used.add(child.id)

        # Exclude function arguments
        arg_names = set()
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            arg_names.add(arg.arg)
        if node.args.vararg:
            arg_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            arg_names.add(node.args.kwarg.arg)

        for name, lineno in assigned.items():
            if name not in used and name not in arg_names:
                self.results.append(f"'{name}' in {node.name}() at line {lineno}")


class FunctionLengthChecker(ast.NodeVisitor):
    """Detect functions longer than 50 lines."""

    MAX_LINES = 50

    def __init__(self) -> None:
        self.results: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def _check(self, node: ast.FunctionDef) -> None:
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            length = end_lineno - node.lineno + 1
            if length > self.MAX_LINES:
                self.results.append(
                    f"{node.name}() at line {node.lineno} ({length} lines)"
                )


class NestingChecker(ast.NodeVisitor):
    """Detect nesting deeper than 4 levels within functions."""

    MAX_DEPTH = 4
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
    )

    def __init__(self) -> None:
        self.results: List[str] = []
        self._reported: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_nesting(node, node.name, 0)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_nesting(node, node.name, 0)

    def _check_nesting(self, node: ast.AST, func_name: str, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.NESTING_NODES):
                new_depth = depth + 1
                if new_depth > self.MAX_DEPTH:
                    key = f"{func_name}:{child.lineno}"
                    if key not in self._reported:
                        self._reported.add(key)
                        block_type = type(child).__name__
                        self.results.append(
                            f"{func_name}() at line {child.lineno} "
                            f"(depth {new_depth}, {block_type})"
                        )
                self._check_nesting(child, func_name, new_depth)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Don't count nested function definitions as nesting
                pass
            else:
                self._check_nesting(child, func_name, depth)


def check_code(source: str) -> CheckResults:
    """Analyze Python source code and return a CheckResults dataclass.

    Detects:
    - Unused imports
    - Unused variables within functions
    - Functions longer than 50 lines
    - Nesting deeper than 4 levels

    Uses ast.NodeVisitor for all analysis (no regex).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.unused_imports.append(f"SyntaxError: {e}")
        return results

    results = CheckResults()

    # 1. Unused imports
    import_collector = ImportCollector()
    import_collector.visit(tree)

    name_collector = NameUsageCollector(set(import_collector.imported_names.keys()))
    name_collector.visit(tree)

    for name, lineno in import_collector.imported_names.items():
        if name not in name_collector.used_names:
            results.unused_imports.append(f"'{name}' at line {lineno}")

    # 2. Unused variables
    var_collector = VariableCollector()
    var_collector.visit(tree)
    results.unused_variables = var_collector.results

    # 3. Long functions
    length_checker = FunctionLengthChecker()
    length_checker.visit(tree)
    results.long_functions = length_checker.results

    # 4. Deep nesting
    nesting_checker = NestingChecker()
    nesting_checker.visit(tree)
    results.deep_nesting = nesting_checker.results

    return results


if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import OrderedDict

def short_function():
    x = 1
    y = 2
    return x

def deeply_nested(data):
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    while sub > 0:
                        print(sub)
                        sub -= 1

def long_function():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    h = 8
    i = 9
    j = 10
    k = 11
    l = 12
    m = 13
    n = 14
    o = 15
    p = 16
    q = 17
    r = 18
    s = 19
    t = 20
    u = 21
    v = 22
    w = 23
    x = 24
    y = 25
    z = 26
    aa = 27
    bb = 28
    cc = 29
    dd = 30
    ee = 31
    ff = 32
    gg = 33
    hh = 34
    ii = 35
    jj = 36
    kk = 37
    ll = 38
    mm = 39
    nn = 40
    oo = 41
    pp = 42
    qq = 43
    rr = 44
    ss = 45
    tt = 46
    uu = 47
    vv = 48
    ww = 49
    xx = 50
    yy = 51
    return a

def uses_os():
    return os.getcwd()
'''

    result = check_code(sample_code)
    print(result)
