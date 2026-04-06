"""AST Code Checker — MC-PY-04 (H × RRR)"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Literal

# ── Result Dataclasses ──
@dataclass
class CheckResult:
    check_type: Literal["unused_import", "unused_variable", "long_function", "deep_nesting"]
    message: str
    line: int
    column: int
    severity: Literal["warning", "error"]
    context: str

@dataclass
class CheckReport:
    issues: list[CheckResult]
    total: int
    by_type: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.by_type = {}
        for issue in self.issues:
            self.by_type[issue.check_type] = self.by_type.get(issue.check_type, 0) + 1

# ── Scope Info ──
@dataclass
class ScopeInfo:
    name: str
    defined: dict[str, int] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)

# ── Import Checker ──
class ImportChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imported: dict[str, int] = {}
        self.used_names: set[str] = set()
        self._results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        # Report unused
        for name, line in self.imported.items():
            if name not in self.used_names:
                self._results.append(
                    CheckResult(
                        check_type="unused_import",
                        message=f"Import '{name}' is imported but never used",
                        line=line,
                        column=0,
                        severity="warning",
                        context=name,
                    )
                )
        return self._results

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name: str = alias.asname if alias.asname else alias.name
            self.imported[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.names:
            for alias in node.names:
                name: str = alias.asname if alias.asname else alias.name
                self.imported[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Handle cases like os.path where 'os' is the used name
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

# ── Variable Checker ──
class VariableChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self._scopes: list[ScopeInfo] = []
        self._results: list[CheckResult] = []
        self._global_scope: ScopeInfo = ScopeInfo(name="<module>")

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self._scopes = [self._global_scope]
        self.visit(tree)
        # Check module scope
        self._check_scope(self._global_scope)
        return self._results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        scope: ScopeInfo = ScopeInfo(name=node.name)

        # Function parameters as defined variables
        for arg in node.args.args:
            scope.defined[arg.arg] = node.lineno
        if node.args.vararg:
            scope.defined[node.args.vararg.arg] = node.lineno
        if node.args.kwarg:
            scope.defined[node.args.kwarg.arg] = node.lineno
        for arg in node.args.kwonlyargs:
            scope.defined[arg.arg] = node.lineno

        self._scopes.append(scope)
        self.generic_visit(node)
        self._scopes.pop()
        self._check_scope(scope)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> None:
        scope: ScopeInfo = self._scopes[-1]
        for target in node.targets:
            if isinstance(target, ast.Name):
                scope.defined[target.id] = node.lineno
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        scope.defined[elt.id] = node.lineno
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        scope: ScopeInfo = self._scopes[-1]
        if isinstance(node.target, ast.Name):
            scope.defined[node.target.id] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            # Mark as used in all enclosing scopes
            for scope in reversed(self._scopes):
                scope.used.add(node.id)
        self.generic_visit(node)

    def _check_scope(self, scope: ScopeInfo) -> None:
        for var_name, line in scope.defined.items():
            # Skip private/conventional unused variables
            if var_name.startswith("_"):
                continue
            # Skip dunder names
            if var_name.startswith("__") and var_name.endswith("__"):
                continue
            # Skip 'self' and 'cls'
            if var_name in ("self", "cls"):
                continue
            if var_name not in scope.used:
                self._results.append(
                    CheckResult(
                        check_type="unused_variable",
                        message=f"Variable '{var_name}' is defined but never used in '{scope.name}'",
                        line=line,
                        column=0,
                        severity="warning",
                        context=var_name,
                    )
                )

# ── Function Length Checker ──
class FunctionLengthChecker(ast.NodeVisitor):
    MAX_LINES: int = 50

    def __init__(self) -> None:
        self._results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        return self._results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        length: int = self._calculate_length(node)
        if length > self.MAX_LINES:
            self._results.append(
                CheckResult(
                    check_type="long_function",
                    message=f"Function '{node.name}' is {length} lines long (max allowed: {self.MAX_LINES})",
                    line=node.lineno,
                    column=node.col_offset,
                    severity="warning",
                    context=node.name,
                )
            )
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _calculate_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if not node.body:
            return 0
        start: int = node.lineno
        end: int = self._last_line(node)
        return end - start + 1

    def _last_line(self, node: ast.AST) -> int:
        max_line: int = getattr(node, "lineno", 0)
        for child in ast.walk(node):
            child_line: int = getattr(child, "end_lineno", 0) or getattr(child, "lineno", 0)
            if child_line > max_line:
                max_line = child_line
        return max_line

# ── Nesting Depth Checker ──
class NestingDepthChecker(ast.NodeVisitor):
    MAX_DEPTH: int = 4

    NESTING_NODES: set[type] = {
        ast.If,
        ast.For,
        ast.While,
        ast.AsyncFor,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
    }

    def __init__(self) -> None:
        self._results: list[CheckResult] = []
        self._current_depth: int = 0
        self._max_depth: int = 0
        self._function_name: str = ""
        self._function_line: int = 0

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        return self._results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        saved_depth: int = self._current_depth
        saved_max: int = self._max_depth
        saved_name: str = self._function_name
        saved_line: int = self._function_line

        self._current_depth = 0
        self._max_depth = 0
        self._function_name = node.name
        self._function_line = node.lineno

        self._visit_body(node.body)

        if self._max_depth > self.MAX_DEPTH:
            self._results.append(
                CheckResult(
                    check_type="deep_nesting",
                    message=f"Function '{node.name}' has nesting depth {self._max_depth} (max allowed: {self.MAX_DEPTH})",
                    line=node.lineno,
                    column=node.col_offset,
                    severity="warning",
                    context=node.name,
                )
            )

        self._current_depth = saved_depth
        self._max_depth = saved_max
        self._function_name = saved_name
        self._function_line = saved_line

    visit_AsyncFunctionDef = visit_FunctionDef

    def _visit_body(self, body: list[ast.stmt]) -> None:
        for node in body:
            if type(node) in self.NESTING_NODES:
                self._current_depth += 1
                if self._current_depth > self._max_depth:
                    self._max_depth = self._current_depth

                # Visit nested bodies
                for attr in ("body", "handlers", "orelse", "finalbody"):
                    child_body: list[ast.stmt] | None = getattr(node, attr, None)
                    if child_body and isinstance(child_body, list):
                        self._visit_body(child_body)

                self._current_depth -= 1
            else:
                # Check for nested functions, classes, etc.
                for attr in ("body", "handlers", "orelse", "finalbody"):
                    child_body = getattr(node, attr, None)
                    if child_body and isinstance(child_body, list):
                        self._visit_body(child_body)

# ── Code Checker (Orchestrator) ──
class CodeChecker:
    """Main entry point. Parses source, runs all checkers, returns results."""

    def check(self, source: str) -> CheckReport:
        try:
            tree: ast.Module = ast.parse(source)
        except SyntaxError as e:
            return CheckReport(
                issues=[
                    CheckResult(
                        check_type="unused_import",  # closest type for parse errors
                        message=f"Syntax error: {e.msg}",
                        line=e.lineno or 0,
                        column=e.offset or 0,
                        severity="error",
                        context="parse_error",
                    )
                ],
                total=1,
            )

        results: list[CheckResult] = []
        results.extend(ImportChecker().run(tree))
        results.extend(VariableChecker().run(tree))
        results.extend(FunctionLengthChecker().run(tree))
        results.extend(NestingDepthChecker().run(tree))

        return CheckReport(issues=results, total=len(results))


# ── Main (demo) ──
if __name__ == "__main__":
    sample_code: str = '''
import os
import sys
from collections import OrderedDict

def short_function():
    x = 10
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

def deeply_nested(data):
    if data:
        for item in data:
            if item > 0:
                while item > 0:
                    if item % 2 == 0:
                        print(item)
                    item -= 1

unused_var = 42
result = short_function()
print(result)
print(sys.version)
'''

    checker = CodeChecker()
    report: CheckReport = checker.check(sample_code)

    print(f"Total issues: {report.total}")
    print(f"By type: {report.by_type}")
    print()
    for issue in report.issues:
        print(f"  [{issue.severity}] L{issue.line}: {issue.message}")
