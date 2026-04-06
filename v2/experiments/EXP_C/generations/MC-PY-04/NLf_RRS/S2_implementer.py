"""AST Code Checker — unused imports, unused variables, long functions, deep nesting."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


# ── Issue Dataclasses ────────────────────────────────────────────────────────


@dataclass
class UnusedImportIssue:
    name: str
    line: int
    module: str | None


@dataclass
class UnusedVariableIssue:
    name: str
    line: int
    scope: str


@dataclass
class LongFunctionIssue:
    function_name: str
    line: int
    length: int
    threshold: int = 50


@dataclass
class DeepNestingIssue:
    function_name: str
    line: int
    max_depth: int
    threshold: int = 4


@dataclass
class CheckResult:
    unused_imports: list[UnusedImportIssue] = field(default_factory=list)
    unused_variables: list[UnusedVariableIssue] = field(default_factory=list)
    long_functions: list[LongFunctionIssue] = field(default_factory=list)
    deep_nesting: list[DeepNestingIssue] = field(default_factory=list)
    total_issues: int = 0
    source_lines: int = 0


# ── ImportCollector ──────────────────────────────────────────────────────────


@dataclass
class ImportInfo:
    name: str
    alias: str | None
    line: int
    module: str | None


class ImportCollector(ast.NodeVisitor):
    """Collects all import names and their line numbers."""

    def __init__(self) -> None:
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            effective_name = alias.asname if alias.asname else alias.name
            self.imports.append(ImportInfo(
                name=effective_name,
                alias=alias.asname,
                line=node.lineno,
                module=None,
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            effective_name = alias.asname if alias.asname else alias.name
            self.imports.append(ImportInfo(
                name=effective_name,
                alias=alias.asname,
                line=node.lineno,
                module=module,
            ))
        self.generic_visit(node)


# ── NameUsageCollector ───────────────────────────────────────────────────────


class NameUsageCollector(ast.NodeVisitor):
    """Collects all name references (loads) in non-import contexts."""

    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Capture base name for module.func patterns
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


# ── VariableTracker ──────────────────────────────────────────────────────────


@dataclass
class VarInfo:
    assigned: bool
    used: bool
    line: int


class VariableTracker(ast.NodeVisitor):
    """Tracks variable assignments and usages per scope."""

    def __init__(self) -> None:
        self.issues: list[UnusedVariableIssue] = []
        self._scope_stack: list[tuple[str, dict[str, VarInfo]]] = []
        self._import_names: set[str] = set()

    def set_import_names(self, names: set[str]) -> None:
        self._import_names = names

    def _push_scope(self, name: str) -> None:
        self._scope_stack.append((name, {}))

    def _pop_scope(self) -> None:
        if not self._scope_stack:
            return
        scope_name, scope_vars = self._scope_stack.pop()
        for var_name, info in scope_vars.items():
            if info.assigned and not info.used:
                if var_name.startswith("_"):
                    continue
                if var_name in self._import_names:
                    continue
                self.issues.append(UnusedVariableIssue(
                    name=var_name,
                    line=info.line,
                    scope=scope_name,
                ))

    def _current_scope(self) -> dict[str, VarInfo]:
        if self._scope_stack:
            return self._scope_stack[-1][1]
        return {}

    def _mark_assigned(self, name: str, line: int) -> None:
        scope = self._current_scope()
        if name not in scope:
            scope[name] = VarInfo(assigned=True, used=False, line=line)
        else:
            scope[name].assigned = True
            scope[name].line = line

    def _mark_used(self, name: str) -> None:
        # Check current scope and parent scopes
        for _, scope_vars in reversed(self._scope_stack):
            if name in scope_vars:
                scope_vars[name].used = True
                return

    def visit_Module(self, node: ast.Module) -> None:
        self._push_scope("<module>")
        self.generic_visit(node)
        self._pop_scope()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope(node.name)
        # Mark parameters as assigned
        for arg in node.args.args:
            self._mark_assigned(arg.arg, node.lineno)
        for arg in node.args.posonlyargs:
            self._mark_assigned(arg.arg, node.lineno)
        for arg in node.args.kwonlyargs:
            self._mark_assigned(arg.arg, node.lineno)
        if node.args.vararg:
            self._mark_assigned(node.args.vararg.arg, node.lineno)
        if node.args.kwarg:
            self._mark_assigned(node.args.kwarg.arg, node.lineno)
        self.generic_visit(node)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._push_scope(node.name)
        for arg in node.args.args:
            self._mark_assigned(arg.arg, node.lineno)
        self.generic_visit(node)
        self._pop_scope()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._mark_assigned(node.id, node.lineno)
        elif isinstance(node.ctx, ast.Load):
            self._mark_used(node.id)
        self.generic_visit(node)


# ── FunctionAnalyzer ─────────────────────────────────────────────────────────


class FunctionAnalyzer(ast.NodeVisitor):
    """Visits function definitions to calculate line count and nesting depth."""

    NESTING_TYPES = (
        ast.If, ast.For, ast.AsyncFor, ast.While,
        ast.With, ast.AsyncWith, ast.Try,
        ast.ExceptHandler, ast.FunctionDef, ast.AsyncFunctionDef,
        ast.ClassDef,
    )

    def __init__(self) -> None:
        self.long_functions: list[LongFunctionIssue] = []
        self.deep_nesting: list[DeepNestingIssue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Check function length
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                self.long_functions.append(LongFunctionIssue(
                    function_name=node.name,
                    line=node.lineno,
                    length=length,
                ))

        # Check nesting depth
        max_depth = self._compute_max_depth(node, 0)
        if max_depth > 4:
            self.deep_nesting.append(DeepNestingIssue(
                function_name=node.name,
                line=node.lineno,
                max_depth=max_depth,
            ))

    def _compute_max_depth(self, node: ast.AST, current_depth: int) -> int:
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.NESTING_TYPES):
                child_max = self._compute_max_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_max)
            else:
                child_max = self._compute_max_depth(child, current_depth)
                max_depth = max(max_depth, child_max)
        return max_depth


# ── CodeChecker ──────────────────────────────────────────────────────────────


class CodeChecker:
    """Python code checker using AST analysis."""

    def check(self, source: str) -> CheckResult:
        """Parse source and run all checks."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return CheckResult(
                source_lines=source.count("\n") + 1,
                total_issues=1,
                unused_imports=[UnusedImportIssue(
                    name=f"SyntaxError: {e.msg}",
                    line=e.lineno or 0,
                    module=None,
                )],
            )

        source_lines = source.count("\n") + 1

        unused_imports = self.check_unused_imports(tree)
        unused_variables = self.check_unused_variables(tree)
        long_functions = self.check_long_functions(tree)
        deep_nesting = self.check_deep_nesting(tree)

        total = len(unused_imports) + len(unused_variables) + len(long_functions) + len(deep_nesting)

        return CheckResult(
            unused_imports=unused_imports,
            unused_variables=unused_variables,
            long_functions=long_functions,
            deep_nesting=deep_nesting,
            total_issues=total,
            source_lines=source_lines,
        )

    def check_unused_imports(self, tree: ast.Module) -> list[UnusedImportIssue]:
        """Find unused imports."""
        collector = ImportCollector()
        collector.visit(tree)

        usage = NameUsageCollector()
        usage.visit(tree)

        issues: list[UnusedImportIssue] = []
        for imp in collector.imports:
            if imp.name not in usage.used_names:
                # Check if the name is used in __all__
                if imp.name.startswith("_"):
                    continue
                issues.append(UnusedImportIssue(
                    name=imp.name,
                    line=imp.line,
                    module=imp.module,
                ))

        return issues

    def check_unused_variables(self, tree: ast.Module) -> list[UnusedVariableIssue]:
        """Find unused variables."""
        # Gather import names to exclude
        collector = ImportCollector()
        collector.visit(tree)
        import_names = {imp.name for imp in collector.imports}

        tracker = VariableTracker()
        tracker.set_import_names(import_names)
        tracker.visit(tree)

        return tracker.issues

    def check_long_functions(self, tree: ast.Module) -> list[LongFunctionIssue]:
        """Find functions longer than 50 lines."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.long_functions

    def check_deep_nesting(self, tree: ast.Module) -> list[DeepNestingIssue]:
        """Find functions with nesting depth exceeding 4."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.deep_nesting


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import OrderedDict

def short_function():
    x = 1
    y = 2
    return x + y

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
    return a

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        break
    return True

def uses_os():
    return os.path.exists("/tmp")
'''

    checker = CodeChecker()
    result = checker.check(sample_code)

    print(f"Source lines: {result.source_lines}")
    print(f"Total issues: {result.total_issues}")

    if result.unused_imports:
        print("\nUnused imports:")
        for issue in result.unused_imports:
            print(f"  Line {issue.line}: {issue.name}" + (f" (from {issue.module})" if issue.module else ""))

    if result.unused_variables:
        print("\nUnused variables:")
        for issue in result.unused_variables:
            print(f"  Line {issue.line}: {issue.name} in {issue.scope}")

    if result.long_functions:
        print("\nLong functions (>50 lines):")
        for issue in result.long_functions:
            print(f"  Line {issue.line}: {issue.function_name} ({issue.length} lines)")

    if result.deep_nesting:
        print("\nDeeply nested functions (>4 levels):")
        for issue in result.deep_nesting:
            print(f"  Line {issue.line}: {issue.function_name} (depth {issue.max_depth})")
