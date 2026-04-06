import ast
from dataclasses import dataclass, field
from typing import List, Set, Dict


@dataclass
class CheckResults:
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[Dict[str, object]] = field(default_factory=list)
    deep_nesting: List[Dict[str, object]] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (
            len(self.unused_imports)
            + len(self.unused_variables)
            + len(self.long_functions)
            + len(self.deep_nesting)
        )

    def summary(self) -> str:
        lines = [f"Code Check Results ({self.total_issues} issues found):"]
        if self.unused_imports:
            lines.append(f"  Unused imports ({len(self.unused_imports)}):")
            for imp in self.unused_imports:
                lines.append(f"    - {imp}")
        if self.unused_variables:
            lines.append(f"  Unused variables ({len(self.unused_variables)}):")
            for var in self.unused_variables:
                lines.append(f"    - {var}")
        if self.long_functions:
            lines.append(f"  Long functions ({len(self.long_functions)}):")
            for func in self.long_functions:
                lines.append(
                    f"    - {func['name']} at line {func['line']}: {func['length']} lines"
                )
        if self.deep_nesting:
            lines.append(f"  Deep nesting ({len(self.deep_nesting)}):")
            for nest in self.deep_nesting:
                lines.append(
                    f"    - {nest['location']} at line {nest['line']}: depth {nest['depth']}"
                )
        return "\n".join(lines)


class _ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imported_names: Dict[str, int] = {}

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


class _NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.used_names: Set[str] = set()

    def visit_Name(self, node: ast.Name):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


class _VariableTracker(ast.NodeVisitor):
    def __init__(self):
        self.assigned: Dict[str, int] = {}
        self.used: Set[str] = set()
        self._in_target = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        tracker = _VariableTracker()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in tracker.assigned:
                        tracker.assigned[child.id] = child.lineno
                elif isinstance(child.ctx, (ast.Load, ast.Del)):
                    tracker.used.add(child.id)

        for arg in node.args.args:
            tracker.used.add(arg.arg)
        if node.args.vararg:
            tracker.used.add(node.args.vararg.arg)
        if node.args.kwarg:
            tracker.used.add(node.args.kwarg.arg)

        for name, lineno in tracker.assigned.items():
            if name.startswith("_"):
                continue
            if name not in tracker.used:
                self.assigned[name] = lineno

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)


class _FunctionLengthChecker(ast.NodeVisitor):
    def __init__(self, max_lines: int = 50):
        self.max_lines = max_lines
        self.long_functions: List[Dict[str, object]] = []

    def _check_function(self, node):
        if not node.body:
            return
        start = node.lineno
        end = max(getattr(n, "end_lineno", n.lineno) for n in ast.walk(node) if hasattr(n, "lineno"))
        length = end - start + 1
        if length > self.max_lines:
            self.long_functions.append({
                "name": node.name,
                "line": node.lineno,
                "length": length,
            })

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)


class _NestingChecker(ast.NodeVisitor):
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
    )

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.deep_nesting: List[Dict[str, object]] = []
        self._current_function: str = "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old = self._current_function
        self._current_function = node.name
        self._check_nesting(node.body, depth=0)
        self._current_function = old

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        old = self._current_function
        self._current_function = node.name
        self._check_nesting(node.body, depth=0)
        self._current_function = old

    def _check_nesting(self, body: list, depth: int):
        for node in body:
            if isinstance(node, self.NESTING_NODES):
                new_depth = depth + 1
                if new_depth > self.max_depth:
                    self.deep_nesting.append({
                        "location": self._current_function,
                        "line": node.lineno,
                        "depth": new_depth,
                    })
                for child_body_attr in ("body", "orelse", "handlers", "finalbody"):
                    child_body = getattr(node, child_body_attr, None)
                    if isinstance(child_body, list):
                        self._check_nesting(child_body, new_depth)
            else:
                for child_body_attr in ("body", "orelse"):
                    child_body = getattr(node, child_body_attr, None)
                    if isinstance(child_body, list):
                        self._check_nesting(child_body, depth)


def check_code(source: str) -> CheckResults:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.unused_imports = [f"SyntaxError at line {e.lineno}: {e.msg}"]
        return results

    results = CheckResults()

    import_collector = _ImportCollector()
    import_collector.visit(tree)

    name_collector = _NameCollector()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name_collector.used_names.add(node.id)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            name_collector.used_names.add(node.value.id)

    for name, lineno in import_collector.imported_names.items():
        if name not in name_collector.used_names:
            results.unused_imports.append(f"{name} (line {lineno})")

    var_tracker = _VariableTracker()
    var_tracker.visit(tree)
    for name, lineno in var_tracker.assigned.items():
        results.unused_variables.append(f"{name} (line {lineno})")

    func_checker = _FunctionLengthChecker(max_lines=50)
    func_checker.visit(tree)
    results.long_functions = func_checker.long_functions

    nesting_checker = _NestingChecker(max_depth=4)
    nesting_checker.visit(tree)
    results.deep_nesting = nesting_checker.deep_nesting

    return results


if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import OrderedDict

def short_function():
    x = 1
    return x

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
    aa = 24
    bb = 25
    cc = 26
    dd = 27
    ee = 28
    ff = 29
    gg = 30
    hh = 31
    ii = 32
    jj = 33
    kk = 34
    ll = 35
    mm = 36
    nn = 37
    oo = 38
    pp = 39
    qq = 40
    rr = 41
    ss = 42
    tt = 43
    uu = 44
    vv = 45
    ww = 46
    xx = 47
    yy = 48
    zz = 49
    aaa = 50
    bbb = 51
    return bbb

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        print("too deep!")
                        break

x = os.path.join("a", "b")
unused_var = 42
'''

    results = check_code(sample_code)
    print(results.summary())
