import ast
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class CheckResults:
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
        lines = [f"Code Check Results ({self.total_issues} issues found):"]
        if self.unused_imports:
            lines.append(f"  Unused imports ({len(self.unused_imports)}):")
            for item in self.unused_imports:
                lines.append(f"    - {item}")
        if self.unused_variables:
            lines.append(f"  Unused variables ({len(self.unused_variables)}):")
            for item in self.unused_variables:
                lines.append(f"    - {item}")
        if self.long_functions:
            lines.append(f"  Long functions (>50 lines) ({len(self.long_functions)}):")
            for item in self.long_functions:
                lines.append(f"    - {item}")
        if self.deep_nesting:
            lines.append(f"  Deep nesting (>4 levels) ({len(self.deep_nesting)}):")
            for item in self.deep_nesting:
                lines.append(f"    - {item}")
        if self.total_issues == 0:
            lines.append("  No issues found!")
        return "\n".join(lines)


class ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imported_names: dict = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)


class NameUsageCollector(ast.NodeVisitor):
    def __init__(self, imported_names: Set[str]):
        self.imported_names = imported_names
        self.used_names: Set[str] = set()

    def visit_Name(self, node: ast.Name):
        if node.id in self.imported_names:
            if isinstance(node.ctx, ast.Load):
                self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name):
            if node.value.id in self.imported_names:
                self.used_names.add(node.value.id)
        self.generic_visit(node)


class VariableAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.assigned: dict = {}
        self.used: Set[str] = set()
        self._scope_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        outer_assigned = self.assigned.copy()
        outer_used = self.used.copy()

        self.assigned = {}
        self.used = set()

        for arg in node.args.args:
            self.assigned[arg.arg] = node.lineno
        if node.args.vararg:
            self.assigned[node.args.vararg.arg] = node.lineno
        if node.args.kwarg:
            self.assigned[node.args.kwarg.arg] = node.lineno

        self.generic_visit(node)

        local_assigned = self.assigned
        local_used = self.used

        self.assigned = outer_assigned
        self.used = outer_used

        self._local_results.append((local_assigned, local_used))

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            if node.id not in self.assigned:
                self.assigned[node.id] = node.lineno
        elif isinstance(node.ctx, (ast.Load, ast.Del)):
            self.used.add(node.id)
        self.generic_visit(node)

    def analyze(self, tree: ast.AST) -> List[str]:
        self._local_results: List[tuple] = []
        self.assigned = {}
        self.used = set()
        self.visit(tree)

        unused = []

        for assigned, used in self._local_results:
            for name, lineno in assigned.items():
                if name.startswith("_"):
                    continue
                if name not in used:
                    unused.append(f"'{name}' at line {lineno}")

        for name, lineno in self.assigned.items():
            if name.startswith("_"):
                continue
            if name not in self.used:
                unused.append(f"'{name}' at line {lineno}")

        return unused


class FunctionLengthChecker(ast.NodeVisitor):
    def __init__(self, max_lines: int = 50):
        self.max_lines = max_lines
        self.long_functions: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            length = node.end_lineno - node.lineno + 1
        else:
            length = self._estimate_length(node)

        if length > self.max_lines:
            self.long_functions.append(
                f"'{node.name}' at line {node.lineno} ({length} lines)"
            )
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _estimate_length(self, node: ast.AST) -> int:
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                max_line = max(max_line, child.lineno)
        return max_line - node.lineno + 1


class NestingChecker(ast.NodeVisitor):
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
    )

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.deep_spots: List[str] = []
        self._current_depth = 0
        self._current_func: str = "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_func = self._current_func
        old_depth = self._current_depth
        self._current_func = node.name
        self._current_depth = 0
        self.generic_visit(node)
        self._current_func = old_func
        self._current_depth = old_depth

    visit_AsyncFunctionDef = visit_FunctionDef

    def _visit_nesting(self, node: ast.AST):
        self._current_depth += 1
        if self._current_depth > self.max_depth:
            self.deep_spots.append(
                f"In '{self._current_func}' at line {node.lineno} "
                f"(depth {self._current_depth})"
            )
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_If(self, node): self._visit_nesting(node)
    def visit_For(self, node): self._visit_nesting(node)
    def visit_While(self, node): self._visit_nesting(node)
    def visit_With(self, node): self._visit_nesting(node)
    def visit_Try(self, node): self._visit_nesting(node)
    def visit_ExceptHandler(self, node): self._visit_nesting(node)


def check_code(source: str) -> CheckResults:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.unused_imports = [f"SyntaxError: {e}"]
        return results

    results = CheckResults()

    # 1. Unused imports
    import_collector = ImportCollector()
    import_collector.visit(tree)

    usage_collector = NameUsageCollector(set(import_collector.imported_names.keys()))
    usage_collector.visit(tree)

    for name, lineno in import_collector.imported_names.items():
        if name not in usage_collector.used_names:
            results.unused_imports.append(f"'{name}' at line {lineno}")

    # 2. Unused variables
    var_analyzer = VariableAnalyzer()
    results.unused_variables = var_analyzer.analyze(tree)

    # 3. Long functions
    length_checker = FunctionLengthChecker(max_lines=50)
    length_checker.visit(tree)
    results.long_functions = length_checker.long_functions

    # 4. Deep nesting
    nesting_checker = NestingChecker(max_depth=4)
    nesting_checker.visit(tree)
    results.deep_nesting = nesting_checker.deep_spots

    return results


if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import OrderedDict

def short_func():
    x = 1
    return x

def long_function_example():
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
    return yy

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        break
    return True

unused_var = "I am never used"
used_var = os.getcwd()
print(used_var)
'''

    result = check_code(sample_code)
    print(result)
