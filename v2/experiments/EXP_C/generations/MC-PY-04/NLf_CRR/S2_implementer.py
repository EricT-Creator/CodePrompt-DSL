"""Python Code Checker — AST-based analysis for unused imports, unused variables, long functions, deep nesting."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Set

# ─── Result Dataclass ─────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Result of a code check."""
    check_type: str
    line: int
    column: int
    message: str
    severity: Literal["error", "warning", "info"]


# ─── Unused Import Checker ────────────────────────────────────────────────────

class UnusedImportChecker(ast.NodeVisitor):
    """Track all imports and detect which are never referenced."""

    def __init__(self) -> None:
        self.imports: Dict[str, tuple] = {}  # name -> (line, col, is_from_import)
        self.used_names: Set[str] = set()
        self.issues: List[CheckResult] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports[name] = (node.lineno, node.col_offset, False)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.names:
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname if alias.asname else alias.name
                self.imports[name] = (node.lineno, node.col_offset, True)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Track the root name of attribute chains (e.g., os.path -> track "os")
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            self.used_names.add(current.id)
        self.generic_visit(node)

    def check(self, tree: ast.AST) -> List[CheckResult]:
        self.visit(tree)
        for name, (line, col, is_from) in self.imports.items():
            if name not in self.used_names:
                self.issues.append(
                    CheckResult(
                        check_type="unused_import",
                        line=line,
                        column=col,
                        message=f"Import '{name}' is never used",
                        severity="warning",
                    )
                )
        return self.issues


# ─── Unused Variable Checker ──────────────────────────────────────────────────

@dataclass
class _Scope:
    """Tracks variable bindings and uses within a scope."""
    bindings: Dict[str, int]  # name -> line
    used: Set[str]


class UnusedVariableChecker(ast.NodeVisitor):
    """Track variable assignments and detect unread variables."""

    def __init__(self) -> None:
        self.scopes: List[_Scope] = []
        self.issues: List[CheckResult] = []
        self._in_function = False

    def _push_scope(self) -> None:
        self.scopes.append(_Scope(bindings={}, used=set()))

    def _pop_scope(self) -> None:
        scope = self.scopes.pop()
        for name, line in scope.bindings.items():
            if name not in scope.used and not name.startswith("_"):
                self.issues.append(
                    CheckResult(
                        check_type="unused_variable",
                        line=line,
                        column=0,
                        message=f"Variable '{name}' is assigned but never used",
                        severity="warning",
                    )
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope()
        # Add arguments as bindings
        for arg in node.args.args:
            self.scopes[-1].bindings[arg.arg] = node.lineno
        prev = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = prev
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._push_scope()
        for arg in node.args.args:
            self.scopes[-1].bindings[arg.arg] = node.lineno
        prev = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = prev
        self._pop_scope()

    def visit_Name(self, node: ast.Name) -> None:
        if not self.scopes:
            self.generic_visit(node)
            return

        if isinstance(node.ctx, ast.Store):
            self.scopes[-1].bindings[node.id] = node.lineno
        elif isinstance(node.ctx, (ast.Load, ast.Del)):
            # Mark as used in nearest scope that has it
            for scope in reversed(self.scopes):
                if node.id in scope.bindings:
                    scope.used.add(node.id)
                    break
        self.generic_visit(node)

    def check(self, tree: ast.AST) -> List[CheckResult]:
        self.visit(tree)
        return self.issues


# ─── Function Length Checker ──────────────────────────────────────────────────

class FunctionLengthChecker:
    """Check for functions exceeding 50 lines."""

    MAX_LINES = 50

    def check(self, tree: ast.AST) -> List[CheckResult]:
        issues: List[CheckResult] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, "end_lineno") and node.end_lineno is not None:
                    length = node.end_lineno - node.lineno + 1
                    if length > self.MAX_LINES:
                        issues.append(
                            CheckResult(
                                check_type="long_function",
                                line=node.lineno,
                                column=node.col_offset,
                                message=f"Function '{node.name}' is {length} lines long (maximum is {self.MAX_LINES})",
                                severity="warning",
                            )
                        )
        return issues


# ─── Nesting Depth Checker ────────────────────────────────────────────────────

class NestingDepthChecker(ast.NodeVisitor):
    """Check for nesting depth exceeding a threshold."""

    NESTING_NODES = (
        ast.If,
        ast.For,
        ast.While,
        ast.With,
        ast.Try,
        ast.ExceptHandler,
    )

    MAX_DEPTH = 4

    def __init__(self, max_depth: int = 4) -> None:
        self.max_depth = max_depth
        self.current_depth = 0
        self.issues: List[CheckResult] = []

    def visit(self, node: ast.AST) -> None:
        is_nesting = isinstance(node, self.NESTING_NODES)

        if is_nesting:
            self.current_depth += 1
            if self.current_depth > self.max_depth:
                line = getattr(node, "lineno", 0)
                col = getattr(node, "col_offset", 0)
                self.issues.append(
                    CheckResult(
                        check_type="deep_nesting",
                        line=line,
                        column=col,
                        message=f"Nesting depth {self.current_depth} exceeds maximum of {self.max_depth}",
                        severity="warning",
                    )
                )

        self.generic_visit(node)

        if is_nesting:
            self.current_depth -= 1

    def check(self, tree: ast.AST) -> List[CheckResult]:
        self.issues = []
        self.current_depth = 0
        self.visit(tree)
        return self.issues


# ─── Main CodeChecker Class ──────────────────────────────────────────────────

class CodeChecker:
    """
    Python code checker using AST analysis.

    Checks:
    - Unused imports
    - Unused variables
    - Functions longer than 50 lines
    - Nesting depth exceeding 4 levels
    """

    def __init__(
        self,
        max_function_length: int = 50,
        max_nesting_depth: int = 4,
    ) -> None:
        self.max_function_length = max_function_length
        self.max_nesting_depth = max_nesting_depth

    def check(self, source_code: str) -> List[CheckResult]:
        """
        Analyze source code and return all issues found.

        Args:
            source_code: Python source code as a string.

        Returns:
            List of CheckResult instances describing found issues.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return [
                CheckResult(
                    check_type="syntax_error",
                    line=e.lineno or 0,
                    column=e.offset or 0,
                    message=f"Syntax error: {e.msg}",
                    severity="error",
                )
            ]

        issues: List[CheckResult] = []

        # Check unused imports
        import_checker = UnusedImportChecker()
        issues.extend(import_checker.check(tree))

        # Check unused variables
        var_checker = UnusedVariableChecker()
        issues.extend(var_checker.check(tree))

        # Check function length
        length_checker = FunctionLengthChecker()
        length_checker.MAX_LINES = self.max_function_length
        issues.extend(length_checker.check(tree))

        # Check nesting depth
        nesting_checker = NestingDepthChecker(max_depth=self.max_nesting_depth)
        issues.extend(nesting_checker.check(tree))

        # Sort by line number
        issues.sort(key=lambda r: (r.line, r.column))

        return issues

    def check_file(self, file_path: str) -> List[CheckResult]:
        """
        Analyze a Python file and return all issues found.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of CheckResult instances.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            return [
                CheckResult(
                    check_type="file_error",
                    line=0,
                    column=0,
                    message=f"Cannot read file: {e}",
                    severity="error",
                )
            ]

        return self.check(source)

    def format_results(self, results: List[CheckResult], file_name: str = "<stdin>") -> str:
        """
        Format check results as a human-readable string.

        Args:
            results: List of CheckResult instances.
            file_name: Name of the file being checked.

        Returns:
            Formatted string report.
        """
        if not results:
            return f"{file_name}: All checks passed ✓"

        lines: List[str] = [f"{file_name}: {len(results)} issue(s) found"]
        for r in results:
            severity_icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(r.severity, "?")
            lines.append(
                f"  {severity_icon} Line {r.line}:{r.column} [{r.check_type}] {r.message}"
            )
        return "\n".join(lines)


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from pathlib import Path

def short_function():
    x = 10
    y = 20
    return x + y

def deeply_nested(data):
    result = []
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    for i in range(sub):
                        if i > 0:
                            if i % 3 == 0:
                                result.append(i)
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

unused_var = "hello"
used_var = json.dumps({"key": "value"})
print(used_var)
'''

    checker = CodeChecker()
    results = checker.check(sample_code)
    print(checker.format_results(results))
