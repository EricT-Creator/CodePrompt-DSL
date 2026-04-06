from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ───────────────────────────────────────────────────────────────

class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CheckType(str, Enum):
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    FUNCTION_TOO_LONG = "function_too_long"
    NESTING_TOO_DEEP = "nesting_too_deep"


# ── Result dataclasses ──────────────────────────────────────────────────

@dataclass
class CheckResult:
    check_type: CheckType
    message: str
    line: int
    col: int = 0
    severity: Severity = Severity.WARNING
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "data": self.data,
        }

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] L{self.line}: {self.message}"


@dataclass
class UnusedImportResult(CheckResult):
    import_name: str = ""
    module: str = ""


@dataclass
class UnusedVariableResult(CheckResult):
    variable_name: str = ""
    scope: str = ""


@dataclass
class FunctionLengthResult(CheckResult):
    function_name: str = ""
    line_count: int = 0
    max_allowed: int = 50


@dataclass
class NestingDepthResult(CheckResult):
    context_type: str = ""
    actual_depth: int = 0
    max_allowed: int = 4


@dataclass
class CheckReport:
    results: list[CheckResult] = field(default_factory=list)
    source_file: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.WARNING)

    def by_type(self, ct: CheckType) -> list[CheckResult]:
        return [r for r in self.results if r.check_type == ct]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "total": len(self.results),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "results": [r.to_dict() for r in self.results],
        }


# ── 1. Unused imports detector ──────────────────────────────────────────

class _ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imports.append({"name": name, "module": alias.name, "alias": alias.asname, "line": node.lineno, "col": node.col_offset})
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.imports.append({"name": name, "module": f"{mod}.{alias.name}", "alias": alias.asname, "line": node.lineno, "col": node.col_offset})
        self.generic_visit(node)


class _NameCollector(ast.NodeVisitor):
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


def _check_unused_imports(tree: ast.Module) -> list[CheckResult]:
    ic = _ImportCollector()
    ic.visit(tree)
    nc = _NameCollector()
    nc.visit(tree)
    results: list[CheckResult] = []
    import_names = {imp["name"] for imp in ic.imports}
    for imp in ic.imports:
        if imp["name"] not in nc.used_names:
            results.append(UnusedImportResult(
                check_type=CheckType.UNUSED_IMPORT,
                message=f"Unused import: '{imp['name']}' (from {imp['module']})",
                line=imp["line"],
                col=imp["col"],
                severity=Severity.WARNING,
                import_name=imp["name"],
                module=imp["module"],
            ))
    return results


# ── 2. Unused variables detector ────────────────────────────────────────

class _ScopeTracker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.results: list[CheckResult] = []
        self._scopes: list[dict[str, dict[str, Any]]] = [{}]
        self._reads: set[str] = set()

    def _current(self) -> dict[str, dict[str, Any]]:
        return self._scopes[-1]

    def _define(self, name: str, line: int) -> None:
        if name.startswith("_"):
            return
        self._current()[name] = {"line": line, "read": False}

    def _read(self, name: str) -> None:
        self._reads.add(name)
        for scope in reversed(self._scopes):
            if name in scope:
                scope[name]["read"] = True
                return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scopes.append({})
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._define(arg.arg, node.lineno)
        if node.args.vararg:
            self._define(node.args.vararg.arg, node.lineno)
        if node.args.kwarg:
            self._define(node.args.kwarg.arg, node.lineno)
        self.generic_visit(node)
        scope = self._scopes.pop()
        self._report_unused(scope, f"function '{node.name}'")

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        for target in node.targets:
            self._extract_targets(target, node.lineno)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            self._define(node.target.id, node.lineno)

    def visit_For(self, node: ast.For) -> None:
        self._extract_targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._read(node.id)
        self.generic_visit(node)

    def _extract_targets(self, target: ast.AST, line: int) -> None:
        if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
            self._define(target.id, line)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._extract_targets(elt, line)

    def _report_unused(self, scope: dict[str, dict[str, Any]], scope_name: str) -> None:
        for name, info in scope.items():
            if not info["read"] and name not in self._reads:
                self.results.append(UnusedVariableResult(
                    check_type=CheckType.UNUSED_VARIABLE,
                    message=f"Unused variable '{name}' in {scope_name}",
                    line=info["line"],
                    severity=Severity.WARNING,
                    variable_name=name,
                    scope=scope_name,
                ))


def _check_unused_variables(tree: ast.Module) -> list[CheckResult]:
    tracker = _ScopeTracker()
    tracker.visit(tree)
    return tracker.results


# ── 3. Function length check ────────────────────────────────────────────

def _check_function_length(tree: ast.Module, max_lines: int = 50) -> list[CheckResult]:
    results: list[CheckResult] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            start = node.lineno
            end = max(_end_line(n) for n in ast.walk(node) if hasattr(n, "lineno"))
            length = end - start + 1
            if length > max_lines:
                results.append(FunctionLengthResult(
                    check_type=CheckType.FUNCTION_TOO_LONG,
                    message=f"Function '{node.name}' is {length} lines (max {max_lines})",
                    line=node.lineno,
                    severity=Severity.WARNING,
                    function_name=node.name,
                    line_count=length,
                    max_allowed=max_lines,
                ))
    return results


def _end_line(node: ast.AST) -> int:
    if hasattr(node, "end_lineno") and node.end_lineno is not None:
        return node.end_lineno
    return getattr(node, "lineno", 0)


# ── 4. Nesting depth check ──────────────────────────────────────────────

_NESTING_TYPES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
if sys.version_info >= (3, 11):
    _NESTING_TYPES = (*_NESTING_TYPES, ast.TryStar) if hasattr(ast, "TryStar") else _NESTING_TYPES


def _check_nesting_depth(tree: ast.Module, max_depth: int = 4) -> list[CheckResult]:
    results: list[CheckResult] = []

    def _walk(node: ast.AST, depth: int, func_name: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _walk(child, 0, child.name)
                continue
            new_depth = depth
            ctx_type = ""
            if isinstance(child, _NESTING_TYPES):
                new_depth = depth + 1
                ctx_type = type(child).__name__
                if new_depth > max_depth:
                    results.append(NestingDepthResult(
                        check_type=CheckType.NESTING_TOO_DEEP,
                        message=f"Nesting depth {new_depth} exceeds max {max_depth} in '{func_name}' ({ctx_type})",
                        line=child.lineno,
                        severity=Severity.WARNING,
                        context_type=ctx_type,
                        actual_depth=new_depth,
                        max_allowed=max_depth,
                    ))
            _walk(child, new_depth, func_name)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _walk(node, 0, node.name)
        else:
            _walk(node, 0, "<module>")

    return results


# ── CodeChecker ─────────────────────────────────────────────────────────

class CodeChecker:
    def __init__(self, max_function_length: int = 50, max_nesting_depth: int = 4) -> None:
        self.max_function_length: int = max_function_length
        self.max_nesting_depth: int = max_nesting_depth

    def check_source(self, source: str, filename: str = "<string>") -> CheckReport:
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            return CheckReport(
                results=[CheckResult(
                    check_type=CheckType.UNUSED_IMPORT,
                    message=f"SyntaxError: {exc.msg}",
                    line=exc.lineno or 0,
                    severity=Severity.ERROR,
                )],
                source_file=filename,
            )

        results: list[CheckResult] = []
        results.extend(_check_unused_imports(tree))
        results.extend(_check_unused_variables(tree))
        results.extend(_check_function_length(tree, self.max_function_length))
        results.extend(_check_nesting_depth(tree, self.max_nesting_depth))
        results.sort(key=lambda r: r.line)
        return CheckReport(results=results, source_file=filename)

    def check_file(self, path: str) -> CheckReport:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        return self.check_source(source, filename=path)


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = '''\
import os
import sys
import json

def short_func():
    x = 1
    y = 2
    return x

def deep_nesting():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        print(i, j)
                        break

class Foo:
    def bar(self):
        pass
'''
    checker = CodeChecker()
    report = checker.check_source(sample, "sample.py")
    for r in report.results:
        print(r)
    print(f"\nTotal: {len(report.results)} issues ({report.error_count} errors, {report.warning_count} warnings)")
