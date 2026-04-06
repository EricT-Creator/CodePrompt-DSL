"""AST Code Checker — MC-PY-04 (H × RRS)"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Literal


# ─── Result dataclasses ───
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


# ─── Scope info (for variable tracking) ───
@dataclass
class ScopeInfo:
    name: str
    defined: dict[str, int] = field(default_factory=dict)    # var_name → line
    used: set[str] = field(default_factory=set)


# ─── Import Checker ───
class ImportChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imported: dict[str, int] = {}      # name → line
        self.used_names: set[str] = set()

    def run(self, tree: ast.Module) -> list[CheckResult]:
        # Phase 1: collect imports
        self._collect_imports(tree)
        # Phase 2: collect name usages
        self._collect_usages(tree)
        # Phase 3: report unused
        results: list[CheckResult] = []
        for name, line in self.imported.items():
            if name not in self.used_names:
                results.append(
                    CheckResult(
                        check_type="unused_import",
                        message=f"Import '{name}' is imported but never used",
                        line=line,
                        column=0,
                        severity="warning",
                        context=name,
                    )
                )
        return results

    def _collect_imports(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    self.imported[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    self.imported[name] = node.lineno

    def _collect_usages(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Track the root of attribute access (e.g., os in os.path)
                root = node
                while isinstance(root, ast.Attribute):
                    root = root.value  # type: ignore[assignment]
                if isinstance(root, ast.Name):
                    self.used_names.add(root.id)


# ─── Variable Checker ───
class VariableChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: list[ScopeInfo] = []
        self.results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.scopes = [ScopeInfo(name="<module>")]
        self.visit(tree)
        self._check_scope(self.scopes[-1])
        return self.results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_function(node)

    def _enter_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        scope = ScopeInfo(name=node.name)
        # Add parameters as defined
        for arg in node.args.args:
            scope.defined[arg.arg] = node.lineno
        for arg in node.args.posonlyargs:
            scope.defined[arg.arg] = node.lineno
        for arg in node.args.kwonlyargs:
            scope.defined[arg.arg] = node.lineno
        if node.args.vararg:
            scope.defined[node.args.vararg.arg] = node.lineno
        if node.args.kwarg:
            scope.defined[node.args.kwarg.arg] = node.lineno

        self.scopes.append(scope)
        self.generic_visit(node)
        finished = self.scopes.pop()
        self._check_scope(finished)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.scopes[-1].defined[target.id] = node.lineno
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self.scopes[-1].defined[node.target.id] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.scopes[-1].used.add(node.id)
        self.generic_visit(node)

    def _check_scope(self, scope: ScopeInfo) -> None:
        for var_name, line in scope.defined.items():
            # Skip private / conventional unused markers
            if var_name.startswith("_"):
                continue
            # Skip dunder names
            if var_name.startswith("__") and var_name.endswith("__"):
                continue
            if var_name not in scope.used:
                self.results.append(
                    CheckResult(
                        check_type="unused_variable",
                        message=f"Variable '{var_name}' is defined but never used in '{scope.name}'",
                        line=line,
                        column=0,
                        severity="warning",
                        context=f"{scope.name}.{var_name}",
                    )
                )


# ─── Function Length Checker ───
class FunctionLengthChecker(ast.NodeVisitor):
    MAX_LINES: int = 50

    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        return self.results

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
        end_line: int = self._get_end_line(node)
        length: int = end_line - start_line + 1
        if length > self.MAX_LINES:
            self.results.append(
                CheckResult(
                    check_type="long_function",
                    message=f"Function '{node.name}' is {length} lines long (max allowed: {self.MAX_LINES})",
                    line=start_line,
                    column=node.col_offset,
                    severity="warning",
                    context=node.name,
                )
            )

    def _get_end_line(self, node: ast.AST) -> int:
        end: int = getattr(node, "end_lineno", 0) or 0
        for child in ast.walk(node):
            child_end = getattr(child, "end_lineno", 0) or 0
            if child_end > end:
                end = child_end
        return end


# ─── Nesting Depth Checker ───
class NestingDepthChecker(ast.NodeVisitor):
    MAX_DEPTH: int = 4
    NESTING_TYPES: tuple[type, ...] = (
        ast.If, ast.For, ast.While, ast.AsyncFor,
        ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler,
    )

    def __init__(self) -> None:
        self.results: list[CheckResult] = []
        self._current_function: str = "<module>"
        self._current_function_line: int = 0
        self._current_depth: int = 0
        self._max_depth: int = 0

    def run(self, tree: ast.Module) -> list[CheckResult]:
        self.visit(tree)
        return self.results

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function_nesting(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function_nesting(node)

    def _check_function_nesting(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        old_func = self._current_function
        old_line = self._current_function_line
        old_depth = self._current_depth
        old_max = self._max_depth

        self._current_function = node.name
        self._current_function_line = node.lineno
        self._current_depth = 0
        self._max_depth = 0

        self.generic_visit(node)

        if self._max_depth > self.MAX_DEPTH:
            self.results.append(
                CheckResult(
                    check_type="deep_nesting",
                    message=f"Function '{node.name}' has nesting depth {self._max_depth} (max allowed: {self.MAX_DEPTH})",
                    line=node.lineno,
                    column=node.col_offset,
                    severity="warning",
                    context=node.name,
                )
            )

        self._current_function = old_func
        self._current_function_line = old_line
        self._current_depth = old_depth
        self._max_depth = old_max

    def visit_If(self, node: ast.If) -> None:
        self._visit_nesting_node(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_nesting_node(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_nesting_node(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_nesting_node(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_nesting_node(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_nesting_node(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_nesting_node(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._visit_nesting_node(node)

    def _visit_nesting_node(self, node: ast.AST) -> None:
        self._current_depth += 1
        if self._current_depth > self._max_depth:
            self._max_depth = self._current_depth
        self.generic_visit(node)
        self._current_depth -= 1


# ─── Code Checker (orchestrator) ───
class CodeChecker:
    def check(self, source: str) -> CheckReport:
        tree: ast.Module = ast.parse(source)
        results: list[CheckResult] = []
        results.extend(ImportChecker().run(tree))
        results.extend(VariableChecker().run(tree))
        results.extend(FunctionLengthChecker().run(tree))
        results.extend(NestingDepthChecker().run(tree))
        return CheckReport(issues=results, total=len(results))


# ─── Main guard ───
if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json

def process_data(items):
    unused_var = 42
    result = []
    for item in items:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    for x in range(sub):
                        if x > 3:
                            while x > 0:
                                result.append(x)
                                x -= 1
    return result

def short_function():
    return "hello"
'''

    checker = CodeChecker()
    report = checker.check(sample_code)
    print(f"Total issues: {report.total}")
    print(f"By type: {report.by_type}")
    for issue in report.issues:
        print(f"  [{issue.severity}] {issue.check_type} (line {issue.line}): {issue.message}")
