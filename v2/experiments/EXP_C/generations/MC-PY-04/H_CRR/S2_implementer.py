"""
MC-PY-04: AST Code Checker
[L]PY310 [D]STDLIB_ONLY [MUST]AST_VISITOR [!D]NO_REGEX [O]DATACLASS [TYPE]FULL_HINTS [CHECK]IMPORT+VAR+LEN+NEST [O]CLASS [FILE]SINGLE
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from typing import Any


# ─── Result Data Models ──────────────────────────────────────────────────────

@dataclass
class Issue:
    """A single code issue."""
    type: str          # 'unused_import', 'unused_var', 'long_function', 'deep_nesting', 'syntax_error'
    message: str
    line: int
    col: int
    severity: str = "warning"


@dataclass
class CheckResult:
    """Complete check results for a file."""
    file_path: str
    issues: list[Issue] = field(default_factory=list)

    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def get_by_type(self, issue_type: str) -> list[Issue]:
        return [i for i in self.issues if i.type == issue_type]

    @property
    def unused_imports(self) -> list[Issue]:
        return self.get_by_type("unused_import")

    @property
    def unused_variables(self) -> list[Issue]:
        return self.get_by_type("unused_var")

    @property
    def long_functions(self) -> list[Issue]:
        return self.get_by_type("long_function")

    @property
    def deep_nesting(self) -> list[Issue]:
        return self.get_by_type("deep_nesting")

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.type] = counts.get(issue.type, 0) + 1
        return counts


@dataclass
class Summary:
    """Summary of all checks."""
    total_files: int
    total_issues: int
    issues_by_type: dict[str, int] = field(default_factory=dict)


# ─── Built-in names ──────────────────────────────────────────────────────────

BUILTINS: set[str] = {
    "print", "len", "range", "enumerate", "zip", "map", "filter", "sorted",
    "reversed", "any", "all", "min", "max", "sum", "abs", "round", "hash",
    "id", "type", "isinstance", "issubclass", "hasattr", "getattr", "setattr", "delattr",
    "callable", "repr", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "frozenset", "bytes", "bytearray", "memoryview", "complex",
    "object", "super", "property", "staticmethod", "classmethod",
    "open", "input", "exec", "eval", "compile",
    "True", "False", "None",
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "StopIteration",
    "ImportError", "ModuleNotFoundError", "FileNotFoundError", "IOError",
    "OSError", "PermissionError", "NotImplementedError", "ZeroDivisionError",
    "OverflowError", "RecursionError", "SystemExit", "KeyboardInterrupt",
    "AssertionError", "ArithmeticError", "LookupError", "NameError",
    "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError",
    "GeneratorExit", "StopAsyncIteration", "Warning", "DeprecationWarning",
    "UserWarning", "FutureWarning", "SyntaxWarning",
    "__name__", "__file__", "__doc__", "__all__", "__init__",
    "__enter__", "__exit__", "__str__", "__repr__", "__len__",
    "__getitem__", "__setitem__", "__delitem__", "__iter__", "__next__",
    "__call__", "__eq__", "__ne__", "__lt__", "__gt__", "__le__", "__ge__",
    "__hash__", "__bool__", "__contains__",
    "self", "cls",
    "annotations",
    "dataclass", "field",
    "breakpoint", "format", "chr", "ord", "hex", "oct", "bin",
    "vars", "dir", "globals", "locals", "help",
    "NotImplemented", "Ellipsis",
}


# ─── Visitors ─────────────────────────────────────────────────────────────────

class ImportVisitor(ast.NodeVisitor):
    """Detect unused imports."""

    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self.imports: dict[str, ast.AST] = {}
        self.used_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name: str = alias.asname if alias.asname else alias.name
            # For dotted imports like 'os.path', store top-level name
            top_name: str = name.split(".")[0]
            self.imports[top_name] = node
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.names:
            for alias in node.names:
                if alias.name == "*":
                    continue
                name: str = alias.asname if alias.asname else alias.name
                self.imports[name] = node
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Track attribute access for dotted names
        self.generic_visit(node)

    def finalize(self) -> None:
        """Call after visiting to produce unused import issues."""
        for name, node in self.imports.items():
            if name not in self.used_names and name not in BUILTINS:
                self.issues.append(Issue(
                    type="unused_import",
                    message=f"Import '{name}' is not used",
                    line=node.lineno,
                    col=node.col_offset,
                ))


class VariableVisitor(ast.NodeVisitor):
    """Detect unused variables (function-level)."""

    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self._scope_stack: list[dict[str, ast.AST]] = []
        self._used_stack: list[set[str]] = []

    def _push_scope(self) -> None:
        self._scope_stack.append({})
        self._used_stack.append(set())

    def _pop_scope(self) -> None:
        defined: dict[str, ast.AST] = self._scope_stack.pop()
        used: set[str] = self._used_stack.pop()

        for name, node in defined.items():
            if name.startswith("_"):
                continue
            if name in BUILTINS:
                continue
            if name not in used:
                self.issues.append(Issue(
                    type="unused_var",
                    message=f"Variable '{name}' is assigned but not used",
                    line=node.lineno,
                    col=node.col_offset,
                ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope()

        # Add parameters as defined
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                self._scope_stack[-1][arg.arg] = node

        self.generic_visit(node)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._push_scope()
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                self._scope_stack[-1][arg.arg] = node
        self.generic_visit(node)
        self._pop_scope()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store) and self._scope_stack:
            self._scope_stack[-1][node.id] = node
        elif isinstance(node.ctx, ast.Load) and self._used_stack:
            self._used_stack[-1].add(node.id)
        self.generic_visit(node)


class FunctionLengthVisitor(ast.NodeVisitor):
    """Detect functions longer than MAX_LINES."""
    MAX_LINES: int = 50

    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            length: int = node.end_lineno - node.lineno + 1
            if length > self.MAX_LINES:
                self.issues.append(Issue(
                    type="long_function",
                    message=f"Function '{node.name}' is {length} lines (max {self.MAX_LINES})",
                    line=node.lineno,
                    col=node.col_offset,
                ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            length: int = node.end_lineno - node.lineno + 1
            if length > self.MAX_LINES:
                self.issues.append(Issue(
                    type="long_function",
                    message=f"Async function '{node.name}' is {length} lines (max {self.MAX_LINES})",
                    line=node.lineno,
                    col=node.col_offset,
                ))
        self.generic_visit(node)


class NestingVisitor(ast.NodeVisitor):
    """Detect nesting depth > MAX_DEPTH."""
    MAX_DEPTH: int = 4

    NESTING_TYPES: tuple[type, ...] = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
    )

    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self._current_depth: int = 0

    def visit(self, node: ast.AST) -> None:
        is_nesting: bool = isinstance(node, self.NESTING_TYPES)

        if is_nesting:
            self._current_depth += 1
            if self._current_depth > self.MAX_DEPTH:
                line: int = getattr(node, "lineno", 0)
                col: int = getattr(node, "col_offset", 0)
                self.issues.append(Issue(
                    type="deep_nesting",
                    message=f"Nesting depth {self._current_depth} exceeds max {self.MAX_DEPTH}",
                    line=line,
                    col=col,
                ))

        self.generic_visit(node)

        if is_nesting:
            self._current_depth -= 1


# ─── Code Checker ─────────────────────────────────────────────────────────────

@dataclass
class CodeChecker:
    """Main code checker class. Runs all AST visitors."""

    max_function_lines: int = 50
    max_nesting_depth: int = 4

    def check(self, source: str, filename: str = "<unknown>") -> CheckResult:
        """Check source code for issues."""
        try:
            tree: ast.Module = ast.parse(source, filename=filename)
        except SyntaxError as e:
            return CheckResult(
                file_path=filename,
                issues=[Issue(
                    type="syntax_error",
                    message=str(e),
                    line=e.lineno or 0,
                    col=e.offset or 0,
                    severity="error",
                )],
            )

        all_issues: list[Issue] = []

        # Import check
        import_visitor = ImportVisitor()
        import_visitor.visit(tree)
        import_visitor.finalize()
        all_issues.extend(import_visitor.issues)

        # Variable check
        var_visitor = VariableVisitor()
        var_visitor.visit(tree)
        all_issues.extend(var_visitor.issues)

        # Function length check
        len_visitor = FunctionLengthVisitor()
        len_visitor.MAX_LINES = self.max_function_lines
        len_visitor.visit(tree)
        all_issues.extend(len_visitor.issues)

        # Nesting depth check
        nesting_visitor = NestingVisitor()
        nesting_visitor.MAX_DEPTH = self.max_nesting_depth
        nesting_visitor.visit(tree)
        all_issues.extend(nesting_visitor.issues)

        # Sort by line number
        all_issues.sort(key=lambda i: (i.line, i.col))

        return CheckResult(file_path=filename, issues=all_issues)

    def check_file(self, path: str) -> CheckResult:
        """Check a file by path."""
        with open(path, "r", encoding="utf-8") as f:
            source: str = f.read()
        return self.check(source, filename=path)

    def check_multiple(self, sources: dict[str, str]) -> tuple[list[CheckResult], Summary]:
        """Check multiple sources. Returns results and summary."""
        results: list[CheckResult] = []
        total_issues: int = 0
        by_type: dict[str, int] = {}

        for filename, source in sources.items():
            result: CheckResult = self.check(source, filename)
            results.append(result)
            total_issues += len(result.issues)
            for issue in result.issues:
                by_type[issue.type] = by_type.get(issue.type, 0) + 1

        summary = Summary(
            total_files=len(sources),
            total_issues=total_issues,
            issues_by_type=by_type,
        )

        return results, summary


# ─── Demo ─────────────────────────────────────────────────────────────────────

def main() -> None:
    sample_code: str = '''
import os
import json
import sys

def short_function():
    x = 1
    y = 2
    return x

def deeply_nested(data):
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    try:
                        if sub > 5:
                            print("deep!")
                    except Exception:
                        pass

class MyClass:
    def method(self):
        unused_var = 42
        return "hello"
'''

    checker = CodeChecker(max_function_lines=50, max_nesting_depth=4)
    result: CheckResult = checker.check(sample_code, "sample.py")

    print(f"File: {result.file_path}")
    print(f"Total issues: {len(result.issues)}")
    print(f"Summary: {result.summary()}")
    print()

    for issue in result.issues:
        print(f"  [{issue.severity.upper()}] L{issue.line}:{issue.col} {issue.type}: {issue.message}")


if __name__ == "__main__":
    main()
