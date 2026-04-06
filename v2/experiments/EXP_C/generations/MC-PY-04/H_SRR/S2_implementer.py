"""MC-PY-04: AST Code Checker — ast.NodeVisitor, unused imports/vars, function length, nesting depth"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ── Severity enum ───────────────────────────────────────────────────

class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


# ── Check result dataclass ──────────────────────────────────────────

@dataclass
class CheckResult:
    rule: str
    severity: Severity
    message: str
    file: str
    line: int
    col: int = 0
    symbol: str = ""

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col} [{self.severity.value}] {self.rule}: {self.message}"


# ── Report dataclass ────────────────────────────────────────────────

@dataclass
class CheckReport:
    file: str
    results: list[CheckResult] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    info: int = 0

    def add(self, result: CheckResult) -> None:
        self.results.append(result)
        if result.severity == Severity.ERROR:
            self.errors += 1
        elif result.severity == Severity.WARNING:
            self.warnings += 1
        else:
            self.info += 1

    def summary(self) -> str:
        return (
            f"{self.file}: {len(self.results)} issues "
            f"({self.errors} errors, {self.warnings} warnings, {self.info} info)"
        )


# ── Unused imports checker ──────────────────────────────────────────

class UnusedImportChecker(ast.NodeVisitor):
    """Detects imported names that are never referenced in the module."""

    def __init__(self) -> None:
        self.imports: dict[str, int] = {}  # name -> line
        self.used_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Collect root name for dotted access
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value  # type: ignore[assignment]
        if isinstance(root, ast.Name):
            self.used_names.add(root.id)
        self.generic_visit(node)

    def get_unused(self) -> list[tuple[str, int]]:
        unused: list[tuple[str, int]] = []
        for name, line in self.imports.items():
            if name not in self.used_names:
                unused.append((name, line))
        return sorted(unused, key=lambda x: x[1])


# ── Unused variable checker ─────────────────────────────────────────

class UnusedVariableChecker(ast.NodeVisitor):
    """Detects local variables assigned but never read within a function."""

    def __init__(self) -> None:
        self.issues: list[tuple[str, int, str]] = []  # (func_name, line, var_name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Collect assigned names
        assigned: dict[str, int] = {}
        read: set[str] = set()

        # Parameter names (not unused)
        param_names: set[str] = set()
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            param_names.add(arg.arg)
        if node.args.vararg:
            param_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            param_names.add(node.args.kwarg.arg)

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in param_names and child.id not in assigned:
                        assigned[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    read.add(child.id)

        for var_name, line in assigned.items():
            if var_name.startswith("_"):
                continue  # Convention: _var is intentionally unused
            if var_name not in read:
                self.issues.append((node.name, line, var_name))


# ── Function length checker ─────────────────────────────────────────

class FunctionLengthChecker(ast.NodeVisitor):
    """Detects functions exceeding 50 lines."""

    MAX_LINES: int = 50

    def __init__(self) -> None:
        self.long_functions: list[tuple[str, int, int]] = []  # (name, start_line, length)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        start = node.lineno
        end = node.end_lineno or start
        length = end - start + 1
        if length > self.MAX_LINES:
            self.long_functions.append((node.name, start, length))


# ── Nesting depth checker ───────────────────────────────────────────

class NestingDepthChecker(ast.NodeVisitor):
    """Detects nesting deeper than 4 levels within functions."""

    MAX_DEPTH: int = 4
    NESTING_NODES: tuple[type, ...] = (
        ast.If, ast.For, ast.While, ast.With, ast.Try,
        ast.AsyncFor, ast.AsyncWith,
    )

    def __init__(self) -> None:
        self.issues: list[tuple[str, int, int]] = []  # (func_name, line, depth)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._walk_depth(node, 0, node.name)

    def _walk_depth(self, node: ast.AST, depth: int, func_name: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.NESTING_NODES):
                new_depth = depth + 1
                if new_depth > self.MAX_DEPTH:
                    self.issues.append((func_name, child.lineno, new_depth))
                self._walk_depth(child, new_depth, func_name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Nested function — restart depth counting
                self._check_function(child)
            else:
                self._walk_depth(child, depth, func_name)


# ── Main CodeChecker class ──────────────────────────────────────────

class CodeChecker:
    """AST-based Python code checker combining all four checks."""

    def __init__(self, max_function_lines: int = 50, max_nesting_depth: int = 4) -> None:
        self.max_function_lines = max_function_lines
        self.max_nesting_depth = max_nesting_depth

    def check_source(self, source: str, filename: str = "<string>") -> CheckReport:
        """Run all checks on source code string."""
        report = CheckReport(file=filename)

        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as e:
            report.add(CheckResult(
                rule="syntax-error",
                severity=Severity.ERROR,
                message=str(e),
                file=filename,
                line=e.lineno or 0,
                col=e.offset or 0,
            ))
            return report

        # 1. Unused imports
        import_checker = UnusedImportChecker()
        import_checker.visit(tree)
        for name, line in import_checker.get_unused():
            report.add(CheckResult(
                rule="unused-import",
                severity=Severity.WARNING,
                message=f"Unused import: '{name}'",
                file=filename,
                line=line,
                symbol=name,
            ))

        # 2. Unused variables
        var_checker = UnusedVariableChecker()
        var_checker.visit(tree)
        for func_name, line, var_name in var_checker.issues:
            report.add(CheckResult(
                rule="unused-variable",
                severity=Severity.WARNING,
                message=f"Unused variable '{var_name}' in function '{func_name}'",
                file=filename,
                line=line,
                symbol=var_name,
            ))

        # 3. Function too long
        length_checker = FunctionLengthChecker()
        length_checker.MAX_LINES = self.max_function_lines
        length_checker.visit(tree)
        for func_name, start_line, length in length_checker.long_functions:
            report.add(CheckResult(
                rule="function-too-long",
                severity=Severity.WARNING,
                message=f"Function '{func_name}' is {length} lines long (max {self.max_function_lines})",
                file=filename,
                line=start_line,
                symbol=func_name,
            ))

        # 4. Nesting too deep
        nesting_checker = NestingDepthChecker()
        nesting_checker.MAX_DEPTH = self.max_nesting_depth
        nesting_checker.visit(tree)
        for func_name, line, depth in nesting_checker.issues:
            report.add(CheckResult(
                rule="nesting-too-deep",
                severity=Severity.WARNING,
                message=f"Nesting depth {depth} in function '{func_name}' exceeds max {self.max_nesting_depth}",
                file=filename,
                line=line,
                symbol=func_name,
            ))

        return report

    def check_file(self, path: str | Path) -> CheckReport:
        """Run all checks on a Python file."""
        p = Path(path)
        source = p.read_text(encoding="utf-8")
        return self.check_source(source, filename=str(p))


# ── CLI demo ────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from pathlib import Path

def short_func():
    x = 1
    y = 2
    unused_var = 42
    return x + y

def deeply_nested(data):
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    while sub > 0:
                        if sub == 1:
                            print("deep!")
                        sub -= 1

def very_long_function():
''' + "\n".join(f"    line_{i} = {i}" for i in range(55)) + '''
    return None
'''

    checker = CodeChecker()
    report = checker.check_source(sample_code, filename="sample.py")

    print(report.summary())
    print()
    for r in report.results:
        print(f"  {r}")
