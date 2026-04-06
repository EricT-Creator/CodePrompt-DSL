from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


# ---- Result Dataclasses ----

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


# ---- Import Visitor ----

class ImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: dict[str, int] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)


# ---- Name Usage Visitor ----

class NameUsageVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # For cases like `os.path`, track the root name
        self.generic_visit(node)


# ---- Variable Visitor ----

@dataclass
class ScopeInfo:
    name: str
    assignments: dict[str, int] = field(default_factory=dict)
    usages: set[str] = field(default_factory=set)


class VariableVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: list[ScopeInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        scope = ScopeInfo(name=node.name)

        # Collect parameter names (exclude from unused check)
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

        # Walk function body to find assignments and usages
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in param_names and not child.id.startswith("_"):
                        scope.assignments[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    scope.usages.add(child.id)

        self.scopes.append(scope)

        # Visit nested functions
        for child_node in ast.iter_child_nodes(node):
            self.visit(child_node)

    def get_unused_variables(self) -> list[UnusedVariable]:
        results: list[UnusedVariable] = []
        for scope in self.scopes:
            for var_name, line in scope.assignments.items():
                if var_name not in scope.usages:
                    results.append(UnusedVariable(
                        name=var_name,
                        line=line,
                        scope=scope.name,
                    ))
        return results


# ---- Function Length Visitor ----

class FunctionLengthVisitor(ast.NodeVisitor):
    def __init__(self, max_length: int = 50) -> None:
        self.max_length: int = max_length
        self.long_functions: list[LongFunction] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_length(node)
        self.generic_visit(node)

    def _check_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            length = end_lineno - node.lineno + 1
            if length > self.max_length:
                self.long_functions.append(LongFunction(
                    name=node.name,
                    line=node.lineno,
                    length=length,
                ))


# ---- Nesting Depth Visitor ----

class NestingDepthVisitor(ast.NodeVisitor):
    def __init__(self, max_depth: int = 4) -> None:
        self.max_depth: int = max_depth
        self.current_depth: int = 0
        self.violations: list[NestingIssue] = []

    def _visit_nesting_node(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            lineno = getattr(node, "lineno", 0)
            self.violations.append(NestingIssue(
                line=lineno,
                depth=self.current_depth,
            ))
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


# ---- Code Checker (Main Class) ----

class CodeChecker:
    def __init__(
        self,
        max_function_length: int = 50,
        max_nesting_depth: int = 4,
    ) -> None:
        self.max_function_length: int = max_function_length
        self.max_nesting_depth: int = max_nesting_depth

    def check(self, source: str) -> CheckResult:
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result = CheckResult()
            return result

        result = CheckResult()

        # 1. Unused imports
        import_visitor = ImportVisitor()
        import_visitor.visit(tree)

        usage_visitor = NameUsageVisitor()
        usage_visitor.visit(tree)

        for name, line in import_visitor.imports.items():
            if name not in usage_visitor.used_names:
                result.unused_imports.append(UnusedImport(name=name, line=line))

        # 2. Unused variables
        var_visitor = VariableVisitor()
        var_visitor.visit(tree)
        result.unused_variables = var_visitor.get_unused_variables()

        # 3. Long functions
        func_visitor = FunctionLengthVisitor(max_length=self.max_function_length)
        func_visitor.visit(tree)
        result.long_functions = func_visitor.long_functions

        # 4. Nesting depth
        nesting_visitor = NestingDepthVisitor(max_depth=self.max_nesting_depth)
        nesting_visitor.visit(tree)
        result.nesting_issues = nesting_visitor.violations

        return result


# ---- Demo ----

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import OrderedDict

def short_function():
    x = 1
    return x

def medium_function(data):
    result = []
    unused_var = "never used"
    for item in data:
        if item > 0:
            result.append(item)
    return result

def deeply_nested(data):
    for i in range(10):
        if i > 0:
            for j in range(10):
                if j > 0:
                    for k in range(10):
                        if k > 0:
                            print(i, j, k)

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
        print(f"  Line {issue.line}: unused import '{issue.name}'")

    print(f"\nUnused variables ({len(result.unused_variables)}):")
    for issue in result.unused_variables:
        print(f"  Line {issue.line}: unused variable '{issue.name}' in {issue.scope}")

    print(f"\nLong functions ({len(result.long_functions)}):")
    for issue in result.long_functions:
        print(f"  Line {issue.line}: function '{issue.name}' is {issue.length} lines long")

    print(f"\nNesting issues ({len(result.nesting_issues)}):")
    for issue in result.nesting_issues:
        print(f"  Line {issue.line}: nesting depth {issue.depth}")
