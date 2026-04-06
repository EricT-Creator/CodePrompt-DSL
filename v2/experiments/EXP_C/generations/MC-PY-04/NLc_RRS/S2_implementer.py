from __future__ import annotations

import ast
from dataclasses import dataclass, field


# ── Result Dataclasses ──

@dataclass
class UnusedImport:
    name: str
    line: int


@dataclass
class UnusedVariable:
    name: str
    line: int
    scope: str


@dataclass
class LongFunction:
    name: str
    line: int
    length: int


@dataclass
class NestingIssue:
    line: int
    depth: int


@dataclass
class CheckResult:
    unused_imports: list[UnusedImport] = field(default_factory=list)
    unused_variables: list[UnusedVariable] = field(default_factory=list)
    long_functions: list[LongFunction] = field(default_factory=list)
    nesting_issues: list[NestingIssue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (
            len(self.unused_imports)
            + len(self.unused_variables)
            + len(self.long_functions)
            + len(self.nesting_issues)
        )


# ── Import Visitor ──

class ImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: dict[str, int] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name: str = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name: str = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)


# ── Name Usage Visitor ──

class NameUsageVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


# ── Variable Visitor ──

@dataclass
class ScopeInfo:
    name: str
    assignments: dict[str, int] = field(default_factory=dict)
    usages: set[str] = field(default_factory=set)


class VariableVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: list[ScopeInfo] = []
        self._current_scope: ScopeInfo | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        parent_scope = self._current_scope
        scope = ScopeInfo(name=node.name)
        self._current_scope = scope

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if not child.id.startswith("_"):
                        if child.id not in scope.assignments:
                            scope.assignments[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    scope.usages.add(child.id)

        param_names: set[str] = set()
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            param_names.add(arg.arg)
        if node.args.vararg:
            param_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            param_names.add(node.args.kwarg.arg)

        for param in param_names:
            scope.assignments.pop(param, None)

        self.scopes.append(scope)
        self._current_scope = parent_scope

        for child_node in ast.iter_child_nodes(node):
            if isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child_node)


# ── Function Length Visitor ──

class FunctionLengthVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.long_functions: list[LongFunction] = []
        self.threshold: int = 50

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def _check_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        start: int = node.lineno
        end: int = node.end_lineno if node.end_lineno is not None else start
        length: int = end - start + 1
        if length > self.threshold:
            self.long_functions.append(
                LongFunction(name=node.name, line=start, length=length)
            )


# ── Nesting Depth Visitor ──

class NestingDepthVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.current_depth: int = 0
        self.max_depth: int = 0
        self.violations: list[NestingIssue] = []
        self.threshold: int = 4

    def _visit_nesting_node(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth
        if self.current_depth > self.threshold:
            line: int = getattr(node, "lineno", 0)
            self.violations.append(NestingIssue(line=line, depth=self.current_depth))
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._visit_nesting_node(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_nesting_node(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_nesting_node(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_nesting_node(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_nesting_node(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_nesting_node(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_nesting_node(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._visit_nesting_node(node)


# ── Code Checker (main class) ──

class CodeChecker:
    def check(self, source: str) -> CheckResult:
        tree: ast.Module = ast.parse(source)
        result = CheckResult()

        import_visitor = ImportVisitor()
        import_visitor.visit(tree)

        usage_visitor = NameUsageVisitor()
        usage_visitor.visit(tree)

        for name, line in import_visitor.imports.items():
            if name not in usage_visitor.used_names:
                result.unused_imports.append(UnusedImport(name=name, line=line))

        var_visitor = VariableVisitor()
        var_visitor.visit(tree)

        for scope in var_visitor.scopes:
            for var_name, line in scope.assignments.items():
                if var_name not in scope.usages:
                    result.unused_variables.append(
                        UnusedVariable(name=var_name, line=line, scope=scope.name)
                    )

        length_visitor = FunctionLengthVisitor()
        length_visitor.visit(tree)
        result.long_functions = length_visitor.long_functions

        nesting_visitor = NestingDepthVisitor()
        nesting_visitor.visit(tree)
        result.nesting_issues = nesting_visitor.violations

        return result


# ── Example Usage ──

if __name__ == "__main__":
    test_source = '''
import os
import sys
import json

def short_function():
    x = 1
    y = 2
    return x

def another_function():
    unused_var = 42
    used_var = 10
    return used_var

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        print(i, j)
                        break

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
'''

    checker = CodeChecker()
    result = checker.check(test_source)

    print(f"Total issues found: {result.total_issues}")

    print("\nUnused imports:")
    for issue in result.unused_imports:
        print(f"  Line {issue.line}: '{issue.name}'")

    print("\nUnused variables:")
    for issue in result.unused_variables:
        print(f"  Line {issue.line}: '{issue.name}' in {issue.scope}")

    print("\nLong functions (>{FunctionLengthVisitor().threshold} lines):")
    for issue in result.long_functions:
        print(f"  Line {issue.line}: '{issue.name}' ({issue.length} lines)")

    print("\nNesting issues (>{NestingDepthVisitor().threshold} levels):")
    for issue in result.nesting_issues:
        print(f"  Line {issue.line}: depth {issue.depth}")
