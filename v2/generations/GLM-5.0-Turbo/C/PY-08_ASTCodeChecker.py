import ast
import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    line: int
    col: int
    severity: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"Line {self.line}, Col {self.col} [{self.severity}] {self.rule}: {self.message}"


@dataclass
class CheckResults:
    issues: List[Issue] = field(default_factory=list)
    unused_imports: List[Issue] = field(default_factory=list)
    unused_vars: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def summary(self) -> str:
        lines = [
            f"Total issues: {self.total}",
            f"  Errors: {self.error_count}",
            f"  Warnings: {self.warning_count}",
            f"  Unused imports: {len(self.unused_imports)}",
            f"  Unused variables: {len(self.unused_vars)}",
            f"  Long functions (>50 lines): {len(self.long_functions)}",
            f"  Deep nesting (>4 levels): {len(self.deep_nesting)}",
        ]
        return "\n".join(lines)


class CodeChecker(ast.NodeVisitor):
    MAX_FUNC_LINES = 50
    MAX_NESTING = 4

    def __init__(self, source: str):
        self.source = source
        self.source_lines = source.splitlines()
        self.results = CheckResults()
        self._imported_names: set = set()
        self._used_names: set = set()
        self._defined_names: set = set()
        self._scope_stack: List[set] = []

    def _line_range(self, node: ast.AST) -> int:
        end = getattr(node, "end_lineno", node.lineno)
        return end - node.lineno + 1

    def _find_nesting_depth(self, node: ast.AST) -> int:
        max_depth = 0

        def walk(n: ast.AST, depth: int):
            nonlocal max_depth
            nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)
            if isinstance(n, nesting_nodes):
                depth += 1
                max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(n):
                walk(child, depth)

        walk(node, 0)
        return max_depth

    def _collect_used_names(self, node: ast.AST):
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                self._used_names.add(n.id)

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    name = alias.asname if alias.asname else alias.name
                    self._imported_names.add(name.split(".")[0])
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    name = alias.asname if alias.asname else alias.name
                    self._imported_names.add(name)

        for stmt in node.body:
            if not isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self._collect_used_names(stmt)

        for stmt in node.body:
            self.visit(stmt)

        self._check_unused_imports()
        self._check_unused_vars(node)

    def _check_unused_imports(self):
        for name in self._imported_names:
            if name not in self._used_names and name not in self._defined_names:
                for i, line in enumerate(self.source_lines, 1):
                    stripped = line.strip()
                    if stripped.startswith("import ") or stripped.startswith("from "):
                        if name in stripped:
                            issue = Issue(
                                line=i, col=0,
                                severity="warning",
                                rule="unused-import",
                                message=f"Imported name '{name}' is never used"
                            )
                            self.results.unused_imports.append(issue)
                            self.results.issues.append(issue)
                            break

    def _check_unused_vars(self, node: ast.Module):
        for n in ast.walk(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scope_used: set = set()
                scope_defined: set = set()
                for child in ast.walk(n):
                    if isinstance(child, ast.Name):
                        if isinstance(child.ctx, ast.Store):
                            scope_defined.add(child.id)
                        elif isinstance(child.ctx, ast.Load):
                            scope_used.add(child.id)
                for var_name in scope_defined:
                    if var_name not in scope_used and not var_name.startswith("_"):
                        issue = Issue(
                            line=n.lineno, col=n.col_offset,
                            severity="warning",
                            rule="unused-variable",
                            message=f"Variable '{var_name}' is defined but never used in function '{n.name}'"
                        )
                        self.results.unused_vars.append(issue)
                        self.results.issues.append(issue)

            elif isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if not name.startswith("_") and name not in self._used_names:
                            issue = Issue(
                                line=n.lineno, col=n.col_offset,
                                severity="warning",
                                rule="unused-variable",
                                message=f"Variable '{name}' is assigned but never used"
                            )
                            self.results.unused_vars.append(issue)
                            self.results.issues.append(issue)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        line_count = self._line_range(node)
        if line_count > self.MAX_FUNC_LINES:
            issue = Issue(
                line=node.lineno, col=node.col_offset,
                severity="warning",
                rule="long-function",
                message=f"Function '{node.name}' is {line_count} lines long (max {self.MAX_FUNC_LINES})"
            )
            self.results.long_functions.append(issue)
            self.results.issues.append(issue)

        nesting = self._find_nesting_depth(node)
        if nesting > self.MAX_NESTING:
            issue = Issue(
                line=node.lineno, col=node.col_offset,
                severity="warning",
                rule="deep-nesting",
                message=f"Function '{node.name}' has nesting depth of {nesting} (max {self.MAX_NESTING})"
            )
            self.results.deep_nesting.append(issue)
            self.results.issues.append(issue)

        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


def check_code(source: str) -> CheckResults:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.issues.append(Issue(
            line=e.lineno or 0, col=e.offset or 0,
            severity="error", rule="syntax-error",
            message=f"Syntax error: {e.msg}"
        ))
        return results

    checker = CodeChecker(source)
    checker.visit(tree)
    return checker.results


def demo():
    sample_code = """import os
import sys
import json
from collections import defaultdict

unused_var = 42

def very_long_function(x, y):
    result = x + y
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
    xx = 24
    yy = 25
    zz = 26
    aaa = 27
    bbb = 28
    ccc = 29
    ddd = 30
    eee = 31
    fff = 32
    ggg = 33
    hhh = 34
    iii = 35
    jjj = 36
    kkk = 37
    lll = 38
    mmm = 39
    nnn = 40
    ooo = 41
    ppp = 42
    qqq = 43
    rrr = 44
    sss = 45
    ttt = 46
    uuu = 47
    vvv = 48
    www = 49
    xxx = 50
    return result

def deeply_nested(data):
    for item in data:
        if item:
            for sub in item:
                if sub:
                    for val in sub:
                        if val:
                            print(val)

def clean_function():
    x = 1
    y = 2
    return x + y
"""

    print("=== AST Code Checker Demo ===\n")
    results = check_code(sample_code)
    for issue in results.issues:
        print(f"  {issue}")
    print(f"\n{results.summary()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r") as f:
            source = f.read()
        results = check_code(source)
        for issue in results.issues:
            print(f"  {issue}")
        print(f"\n{results.summary()}")
    else:
        demo()
