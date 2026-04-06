"""AST Code Checker — MC-PY-04 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Literal


# ─── Result Dataclasses ───


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


@dataclass
class ScopeInfo:
    name: str
    defined: dict[str, int] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)


# ─── Import Checker ───


class ImportChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imported: dict[str, int] = {}
        self.used_names: set[str] = set()
        self._results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        # Phase 1: collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name: str = alias.asname if alias.asname else alias.name
                    self.imported[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    self.imported[name] = node.lineno

        # Phase 2: collect all name usages
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle cases like os.path — "os" is used
                root: ast.expr = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    self.used_names.add(root.id)

        # Phase 3: report unused
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


# ─── Variable Checker ───


class VariableChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self._scopes: list[ScopeInfo] = []
        self._results: list[CheckResult] = []
        self._global_scope: ScopeInfo = ScopeInfo(name="<module>")

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self._scopes = [self._global_scope]
        self.visit(tree)
        # Check module-level scope
        self._check_scope(self._global_scope)
        return self._results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        scope: ScopeInfo = ScopeInfo(name=node.name)
        # Add parameters as defined
        for arg in node.args.args:
            scope.defined[arg.arg] = node.lineno
        if node.args.vararg:
            scope.defined[node.args.vararg.arg] = node.lineno
        if node.args.kwarg:
            scope.defined[node.args.kwarg.arg] = node.lineno
        for arg in node.args.kwonlyargs:
            scope.defined[arg.arg] = node.lineno
        for arg in node.args.posonlyargs:
            scope.defined[arg.arg] = node.lineno

        self._scopes.append(scope)
        self.generic_visit(node)
        self._scopes.pop()
        self._check_scope(scope)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._current_scope().defined[target.id] = node.lineno
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self._current_scope().defined[node.target.id] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._current_scope().used.add(node.id)
        self.generic_visit(node)

    def _current_scope(self) -> ScopeInfo:
        return self._scopes[-1]

    def _check_scope(self, scope: ScopeInfo) -> None:
        for var_name, line in scope.defined.items():
            if var_name.startswith("_"):
                continue
            if var_name.startswith("__") and var_name.endswith("__"):
                continue
            if var_name == "self" or var_name == "cls":
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


# ─── Function Length Checker ───


class FunctionLengthChecker(ast.NodeVisitor):
    MAX_LINES: int = 50

    def __init__(self) -> None:
        self._results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        return self._results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def _check_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.body:
            return
        start_line: int = node.lineno
        end_line: int = node.end_lineno if node.end_lineno else start_line
        length: int = end_line - start_line + 1
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


# ─── Nesting Depth Checker ───


class NestingDepthChecker(ast.NodeVisitor):
    MAX_DEPTH: int = 4
    NESTING_TYPES: tuple[type, ...] = (
        ast.If,
        ast.For,
        ast.While,
        ast.AsyncFor,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
    )

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
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        prev_depth: int = self._current_depth
        prev_max: int = self._max_depth
        prev_name: str = self._function_name
        prev_line: int = self._function_line

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

        self._current_depth = prev_depth
        self._max_depth = prev_max
        self._function_name = prev_name
        self._function_line = prev_line

    def _visit_body(self, stmts: list[ast.stmt]) -> None:
        for stmt in stmts:
            if isinstance(stmt, self.NESTING_TYPES):
                self._current_depth += 1
                self._max_depth = max(self._max_depth, self._current_depth)
                # Visit child bodies
                for child_body_attr in ("body", "handlers", "orelse", "finalbody"):
                    child_body: list[ast.stmt] | None = getattr(stmt, child_body_attr, None)
                    if child_body:
                        self._visit_body(child_body)
                self._current_depth -= 1
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Nested function — check separately
                self._check_function(stmt)
            else:
                # Visit any nested bodies (e.g., comprehensions)
                for child_body_attr in ("body", "orelse"):
                    child_body = getattr(stmt, child_body_attr, None)
                    if child_body and isinstance(child_body, list):
                        self._visit_body(child_body)


# ─── Code Checker (Orchestrator) ───


class CodeChecker:
    def check(self, source: str) -> CheckReport:
        try:
            tree: ast.Module = ast.parse(source)
        except SyntaxError as e:
            return CheckReport(
                issues=[
                    CheckResult(
                        check_type="unused_import",
                        message=f"Syntax error: {e.msg}",
                        line=e.lineno or 0,
                        column=e.offset or 0,
                        severity="error",
                        context="syntax",
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


# ─── Demo ───

if __name__ == "__main__":
    sample_code: str = '''
import os
import sys
import json

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

unused_var = "hello"
result = short_function()
print(result)
print(sys.version)
'''

    checker: CodeChecker = CodeChecker()
    report: CheckReport = checker.check(sample_code)

    print(f"Total issues: {report.total}")
    print(f"By type: {report.by_type}")
    print()
    for issue in report.issues:
        print(
            f"  [{issue.severity}] L{issue.line}: {issue.check_type} — {issue.message}"
        )
