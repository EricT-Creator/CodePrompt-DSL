"""AST Code Checker — unused imports, unused variables, long functions, deep nesting."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


# ── Dataclass Result Schema ──────────────────────────────────────────────────


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


# ── Import Collector ─────────────────────────────────────────────────────────


@dataclass
class ImportInfo:
    name: str
    alias: str | None
    line: int
    module: str | None


class ImportCollector(ast.NodeVisitor):
    """Collect all import names and their line numbers."""

    def __init__(self) -> None:
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            effective_name = alias.asname if alias.asname else alias.name
            self.imports.append(
                ImportInfo(
                    name=effective_name,
                    alias=alias.asname,
                    line=node.lineno,
                    module=None,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            effective_name = alias.asname if alias.asname else alias.name
            self.imports.append(
                ImportInfo(
                    name=effective_name,
                    alias=alias.asname,
                    line=node.lineno,
                    module=module_name,
                )
            )
        self.generic_visit(node)


# ── Name Usage Collector ─────────────────────────────────────────────────────


class NameUsageCollector(ast.NodeVisitor):
    """Collect all name references (loads) in non-import contexts."""

    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Capture the root name in attribute chains like module.func
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value  # type: ignore[assignment]
        if isinstance(root, ast.Name):
            self.used_names.add(root.id)
        self.generic_visit(node)


# ── Variable Tracker ─────────────────────────────────────────────────────────


@dataclass
class VarInfo:
    name: str
    line: int
    assigned: bool = True
    used: bool = False


class VariableTracker(ast.NodeVisitor):
    """Track variable assignments and usages per scope."""

    def __init__(self) -> None:
        self.issues: list[UnusedVariableIssue] = []
        self._scope_stack: list[tuple[str, dict[str, VarInfo]]] = []
        self._push_scope("<module>")

    def _push_scope(self, name: str) -> None:
        self._scope_stack.append((name, {}))

    def _pop_scope(self) -> None:
        scope_name, variables = self._scope_stack.pop()
        for var_name, info in variables.items():
            if info.assigned and not info.used and not var_name.startswith("_"):
                self.issues.append(
                    UnusedVariableIssue(
                        name=var_name,
                        line=info.line,
                        scope=scope_name,
                    )
                )

    def _mark_assigned(self, name: str, line: int) -> None:
        if not self._scope_stack:
            return
        _, variables = self._scope_stack[-1]
        if name not in variables:
            variables[name] = VarInfo(name=name, line=line)

    def _mark_used(self, name: str) -> None:
        # Search from innermost scope outward
        for _, variables in reversed(self._scope_stack):
            if name in variables:
                variables[name].used = True
                return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope(node.name)
        # Track parameters as assigned
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

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._mark_assigned(node.id, node.lineno)
        elif isinstance(node.ctx, ast.Load):
            self._mark_used(node.id)
        self.generic_visit(node)

    def finalize(self) -> None:
        while self._scope_stack:
            self._pop_scope()


# ── Function Analyzer ────────────────────────────────────────────────────────

NESTING_TYPES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
)


class FunctionAnalyzer(ast.NodeVisitor):
    """Visit function definitions to calculate line count and nesting depth."""

    def __init__(self) -> None:
        self.long_functions: list[LongFunctionIssue] = []
        self.deep_nesting: list[DeepNestingIssue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        # Function length
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            length = end_lineno - node.lineno + 1
            if length > 50:
                self.long_functions.append(
                    LongFunctionIssue(
                        function_name=node.name,
                        line=node.lineno,
                        length=length,
                    )
                )

        # Nesting depth
        max_depth = self._compute_max_depth(node.body, 0)
        if max_depth > 4:
            self.deep_nesting.append(
                DeepNestingIssue(
                    function_name=node.name,
                    line=node.lineno,
                    max_depth=max_depth,
                )
            )

    def _compute_max_depth(
        self, nodes: list[ast.stmt], current_depth: int
    ) -> int:
        max_d = current_depth

        for node in nodes:
            if isinstance(node, NESTING_TYPES):
                child_depth = current_depth + 1
                if child_depth > max_d:
                    max_d = child_depth

                # Recurse into child bodies
                for attr_name in ("body", "handlers", "orelse", "finalbody"):
                    body = getattr(node, attr_name, None)
                    if body and isinstance(body, list):
                        sub = self._compute_max_depth(body, child_depth)
                        if sub > max_d:
                            max_d = sub
            else:
                # Check for nested bodies in non-nesting nodes (e.g. nested function)
                for attr_name in ("body", "orelse", "finalbody"):
                    body = getattr(node, attr_name, None)
                    if body and isinstance(body, list):
                        sub = self._compute_max_depth(body, current_depth)
                        if sub > max_d:
                            max_d = sub

        return max_d


# ── CodeChecker ──────────────────────────────────────────────────────────────


class CodeChecker:
    """Python code checker using AST analysis."""

    def check(self, source: str) -> CheckResult:
        """Parse source, run all checks, aggregate results."""
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return CheckResult(
                source_lines=source.count("\n") + 1,
                total_issues=1,
                unused_imports=[
                    UnusedImportIssue(
                        name=f"SyntaxError: {exc.msg}",
                        line=exc.lineno or 0,
                        module=None,
                    )
                ],
            )

        source_lines = source.count("\n") + 1

        unused_imports = self.check_unused_imports(tree)
        unused_variables = self.check_unused_variables(tree)
        long_functions = self.check_long_functions(tree)
        deep_nesting = self.check_deep_nesting(tree)

        total = (
            len(unused_imports)
            + len(unused_variables)
            + len(long_functions)
            + len(deep_nesting)
        )

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
        import_collector = ImportCollector()
        import_collector.visit(tree)

        usage_collector = NameUsageCollector()
        usage_collector.visit(tree)

        issues: list[UnusedImportIssue] = []
        for imp in import_collector.imports:
            if imp.name.startswith("_"):
                continue
            if imp.name not in usage_collector.used_names:
                issues.append(
                    UnusedImportIssue(
                        name=imp.name,
                        line=imp.line,
                        module=imp.module,
                    )
                )

        return issues

    def check_unused_variables(self, tree: ast.Module) -> list[UnusedVariableIssue]:
        """Find unused variables."""
        tracker = VariableTracker()
        tracker.visit(tree)
        tracker.finalize()
        return tracker.issues

    def check_long_functions(self, tree: ast.Module) -> list[LongFunctionIssue]:
        """Find functions longer than 50 lines."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.long_functions

    def check_deep_nesting(self, tree: ast.Module) -> list[DeepNestingIssue]:
        """Find functions with nesting depth > 4."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.deep_nesting


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
from collections import OrderedDict

def short_function():
    x = 10
    return x

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        print(i, j)
                        break

def unused_var_example():
    a = 1
    b = 2
    c = 3
    return a + b
'''

    checker = CodeChecker()
    result = checker.check(sample_code)

    print(f"Source lines: {result.source_lines}")
    print(f"Total issues: {result.total_issues}")
    print()

    if result.unused_imports:
        print("Unused Imports:")
        for issue in result.unused_imports:
            print(f"  Line {issue.line}: {issue.name} (from {issue.module})")
        print()

    if result.unused_variables:
        print("Unused Variables:")
        for issue in result.unused_variables:
            print(f"  Line {issue.line}: {issue.name} in {issue.scope}")
        print()

    if result.long_functions:
        print("Long Functions (>50 lines):")
        for issue in result.long_functions:
            print(f"  Line {issue.line}: {issue.function_name} ({issue.length} lines)")
        print()

    if result.deep_nesting:
        print("Deep Nesting (>4 levels):")
        for issue in result.deep_nesting:
            print(f"  Line {issue.line}: {issue.function_name} (depth {issue.max_depth})")
