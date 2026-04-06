from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


# ─── Result Dataclasses ───────────────────────────────────────────────────────

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


# ─── Import Visitor ───────────────────────────────────────────────────────────

class ImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: dict[str, int] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if "." in name:
                name = name.split(".")[0]
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)


# ─── Name Usage Visitor ───────────────────────────────────────────────────────

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


# ─── Variable Visitor ─────────────────────────────────────────────────────────

@dataclass
class _ScopeInfo:
    name: str
    assignments: dict[str, int] = field(default_factory=dict)
    usages: set[str] = field(default_factory=set)


class VariableVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: list[_ScopeInfo] = []
        self._current_scope: _ScopeInfo = _ScopeInfo(name="<module>")
        self.function_scopes: list[_ScopeInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        parent = self._current_scope
        scope = _ScopeInfo(name=node.name)

        param_names: set[str] = set()
        for arg in node.args.args:
            param_names.add(arg.arg)
        for arg in node.args.posonlyargs:
            param_names.add(arg.arg)
        for arg in node.args.kwonlyargs:
            param_names.add(arg.arg)
        if node.args.vararg:
            param_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            param_names.add(node.args.kwarg.arg)

        self._current_scope = scope

        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in param_names and not child.id.startswith("_"):
                        scope.assignments[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    scope.usages.add(child.id)

        self.function_scopes.append(scope)
        self._current_scope = parent

        for child_node in ast.iter_child_nodes(node):
            if isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child_node)


# ─── Function Length Visitor ──────────────────────────────────────────────────

class FunctionLengthVisitor(ast.NodeVisitor):
    MAX_LENGTH: int = 50

    def __init__(self) -> None:
        self.long_functions: list[LongFunction] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def _check_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_line = getattr(node, "end_lineno", None)
        if end_line is not None:
            length = end_line - node.lineno + 1
            if length > self.MAX_LENGTH:
                self.long_functions.append(
                    LongFunction(name=node.name, line=node.lineno, length=length)
                )


# ─── Nesting Depth Visitor ────────────────────────────────────────────────────

class NestingDepthVisitor(ast.NodeVisitor):
    MAX_DEPTH: int = 4

    def __init__(self) -> None:
        self.current_depth: int = 0
        self.violations: list[NestingIssue] = []

    def _visit_nesting_node(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.MAX_DEPTH:
            lineno = getattr(node, "lineno", 0)
            self.violations.append(NestingIssue(line=lineno, depth=self.current_depth))
        self.generic_visit(node)
        self.current_depth -= 1

    visit_If = _visit_nesting_node
    visit_For = _visit_nesting_node
    visit_AsyncFor = _visit_nesting_node
    visit_While = _visit_nesting_node
    visit_With = _visit_nesting_node
    visit_AsyncWith = _visit_nesting_node
    visit_Try = _visit_nesting_node


# ─── Code Checker ─────────────────────────────────────────────────────────────

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

        for scope in var_visitor.function_scopes:
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


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json

def short_function():
    x = 1
    return x

def medium_function(data):
    unused_var = 42
    result = []
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    for i in range(sub):
                        if i > 0:
                            for j in range(i):
                                result.append(j)
    return result

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

x = os.path.join("a", "b")
'''

    checker = CodeChecker()
    result = checker.check(sample_code)

    print(f"Total issues: {result.total_issues}")
    print(f"\nUnused imports ({len(result.unused_imports)}):")
    for issue in result.unused_imports:
        print(f"  Line {issue.line}: '{issue.name}'")

    print(f"\nUnused variables ({len(result.unused_variables)}):")
    for issue in result.unused_variables:
        print(f"  Line {issue.line}: '{issue.name}' in {issue.scope}")

    print(f"\nLong functions ({len(result.long_functions)}):")
    for issue in result.long_functions:
        print(f"  Line {issue.line}: '{issue.name}' ({issue.length} lines)")

    print(f"\nNesting issues ({len(result.nesting_issues)}):")
    for issue in result.nesting_issues:
        print(f"  Line {issue.line}: depth {issue.depth}")
