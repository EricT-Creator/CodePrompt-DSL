from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# ─── Result Dataclasses ───

@dataclass
class UnusedImportResult:
    name: str
    line: int
    column: int
    message: str = field(init=False)

    def __post_init__(self) -> None:
        self.message = f"Unused import: {self.name}"


@dataclass
class UnusedVariableResult:
    name: str
    line: int
    column: int
    scope: str
    message: str = field(init=False)

    def __post_init__(self) -> None:
        self.message = f"Unused variable: {self.name}"


@dataclass
class LongFunctionResult:
    func_name: str
    line: int
    column: int
    line_count: int
    message: str = field(init=False)

    def __post_init__(self) -> None:
        self.message = f"Function '{self.func_name}' is {self.line_count} lines (max 50)"


@dataclass
class DeepNestingResult:
    func_name: str
    line: int
    column: int
    max_depth: int
    message: str = field(init=False)

    def __post_init__(self) -> None:
        self.message = f"Function '{self.func_name}' has nesting depth {self.max_depth} (max 4)"


@dataclass
class CodeCheckResults:
    """Container for all check results."""
    unused_imports: list[UnusedImportResult] = field(default_factory=list)
    unused_variables: list[UnusedVariableResult] = field(default_factory=list)
    long_functions: list[LongFunctionResult] = field(default_factory=list)
    deep_nesting: list[DeepNestingResult] = field(default_factory=list)

    def has_issues(self) -> bool:
        return any([
            self.unused_imports,
            self.unused_variables,
            self.long_functions,
            self.deep_nesting,
        ])

    def total_issues(self) -> int:
        return sum([
            len(self.unused_imports),
            len(self.unused_variables),
            len(self.long_functions),
            len(self.deep_nesting),
        ])

    def summary(self) -> str:
        parts: list[str] = []
        if self.unused_imports:
            parts.append(f"{len(self.unused_imports)} unused import(s)")
        if self.unused_variables:
            parts.append(f"{len(self.unused_variables)} unused variable(s)")
        if self.long_functions:
            parts.append(f"{len(self.long_functions)} long function(s)")
        if self.deep_nesting:
            parts.append(f"{len(self.deep_nesting)} deeply nested function(s)")
        if not parts:
            return "No issues found."
        return "Found: " + ", ".join(parts)


# ─── Import Visitor ───

class ImportVisitor(ast.NodeVisitor):
    """Visitor for tracking imports and their usage."""

    def __init__(self) -> None:
        self.imports: dict[str, ast.AST] = {}
        self.used_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Track base name for module.attr usage
        base = node
        while isinstance(base, ast.Attribute):
            base = base.value
        if isinstance(base, ast.Name):
            self.used_names.add(base.id)
        self.generic_visit(node)


# ─── Variable Visitor ───

class VariableVisitor(ast.NodeVisitor):
    """Visitor for tracking variable assignments and usage."""

    def __init__(self) -> None:
        self.assignments: list[tuple[str, int, int, str]] = []  # (name, line, col, scope)
        self.used_names: set[str] = set()
        self._scope_stack: list[str] = ["<module>"]
        # Names that should not be flagged
        self._builtins: set[str] = {
            "__name__", "__file__", "__doc__", "__all__",
            "_", "__", "self", "cls",
        }

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope_stack.append(node.name)
        # Don't track parameters as unused
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._collect_targets(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.target and node.value:
            self._collect_targets(node.target)
        self.generic_visit(node)

    def _collect_targets(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            name = target.id
            if name not in self._builtins and not name.startswith("_"):
                scope = self._scope_stack[-1]
                self.assignments.append((name, target.lineno, target.col_offset, scope))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_targets(elt)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)


# ─── Nesting Depth Visitor ───

class NestingDepthVisitor(ast.NodeVisitor):
    """Calculate maximum nesting depth for each function."""

    NESTING_TYPES: tuple[type, ...] = (
        ast.If, ast.For, ast.While, ast.With, ast.Try,
    )

    def __init__(self) -> None:
        self.function_depths: dict[str, int] = {}
        self.function_lines: dict[str, tuple[int, int]] = {}  # name -> (line, col)
        self._current_function: str | None = None
        self._current_depth: int = 0
        self._max_depth: int = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        outer_func = self._current_function
        outer_depth = self._current_depth
        outer_max = self._max_depth

        self._current_function = node.name
        self._current_depth = 0
        self._max_depth = 0

        self.generic_visit(node)

        self.function_depths[node.name] = self._max_depth
        self.function_lines[node.name] = (node.lineno, node.col_offset)

        self._current_function = outer_func
        self._current_depth = outer_depth
        self._max_depth = outer_max

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        outer_func = self._current_function
        outer_depth = self._current_depth
        outer_max = self._max_depth

        self._current_function = node.name
        self._current_depth = 0
        self._max_depth = 0

        self.generic_visit(node)

        self.function_depths[node.name] = self._max_depth
        self.function_lines[node.name] = (node.lineno, node.col_offset)

        self._current_function = outer_func
        self._current_depth = outer_depth
        self._max_depth = outer_max

    def _enter_nesting(self, node: ast.AST) -> None:
        if self._current_function is not None:
            self._current_depth += 1
            self._max_depth = max(self._max_depth, self._current_depth)
        self.generic_visit(node)
        if self._current_function is not None:
            self._current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._enter_nesting(node)

    def visit_For(self, node: ast.For) -> None:
        self._enter_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self._enter_nesting(node)

    def visit_With(self, node: ast.With) -> None:
        self._enter_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._enter_nesting(node)


# ─── Main Checker ───

class PythonCodeChecker:
    """AST-based Python code checker."""

    MAX_FUNCTION_LINES: int = 50
    MAX_NESTING_DEPTH: int = 4

    def __init__(self, source: str) -> None:
        self.source: str = source
        self.lines: list[str] = source.split("\n")
        try:
            self.tree: ast.Module = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

    def check(self) -> CodeCheckResults:
        """Run all checks and return results."""
        results = CodeCheckResults()
        results.unused_imports = self._check_unused_imports()
        results.unused_variables = self._check_unused_variables()
        results.long_functions = self._check_long_functions()
        results.deep_nesting = self._check_deep_nesting()
        return results

    def _check_unused_imports(self) -> list[UnusedImportResult]:
        """Check for unused imports."""
        visitor = ImportVisitor()
        visitor.visit(self.tree)

        unused: list[UnusedImportResult] = []
        for name, node in visitor.imports.items():
            if name not in visitor.used_names:
                unused.append(UnusedImportResult(
                    name=name,
                    line=node.lineno,
                    column=node.col_offset,
                ))
        return unused

    def _check_unused_variables(self) -> list[UnusedVariableResult]:
        """Check for unused variables."""
        visitor = VariableVisitor()
        visitor.visit(self.tree)

        unused: list[UnusedVariableResult] = []
        for name, line, col, scope in visitor.assignments:
            if name not in visitor.used_names:
                unused.append(UnusedVariableResult(
                    name=name,
                    line=line,
                    column=col,
                    scope=scope,
                ))
        return unused

    def _check_long_functions(self) -> list[LongFunctionResult]:
        """Check for functions longer than MAX_FUNCTION_LINES."""
        long_funcs: list[LongFunctionResult] = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", None)
                if end_line is not None:
                    line_count = end_line - node.lineno + 1
                else:
                    # Fallback: estimate from body
                    line_count = self._estimate_function_length(node)
                if line_count > self.MAX_FUNCTION_LINES:
                    long_funcs.append(LongFunctionResult(
                        func_name=node.name,
                        line=node.lineno,
                        column=node.col_offset,
                        line_count=line_count,
                    ))
        return long_funcs

    def _estimate_function_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Estimate function length when end_lineno is not available."""
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                max_line = max(max_line, child.lineno)
        return max_line - node.lineno + 1

    def _check_deep_nesting(self) -> list[DeepNestingResult]:
        """Check for nesting depth exceeding MAX_NESTING_DEPTH."""
        visitor = NestingDepthVisitor()
        visitor.visit(self.tree)

        deep_funcs: list[DeepNestingResult] = []
        for func_name, depth in visitor.function_depths.items():
            if depth > self.MAX_NESTING_DEPTH:
                line, col = visitor.function_lines.get(func_name, (0, 0))
                deep_funcs.append(DeepNestingResult(
                    func_name=func_name,
                    line=line,
                    column=col,
                    max_depth=depth,
                ))
        return deep_funcs


# ─── Demo / Main ───

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from pathlib import Path

x = 10
y = 20
used_var = 42

def short_function():
    return used_var

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
    aa = 24
    bb = 25
    cc = 26
    dd = 27
    ee = 28
    ff = 29
    gg = 30
    hh = 31
    ii = 32
    jj = 33
    kk = 34
    ll = 35
    mm = 36
    nn = 37
    oo = 38
    pp = 39
    qq = 40
    rr = 41
    ss = 42
    tt = 43
    uu = 44
    vv = 45
    ww = 46
    xx = 47
    yy = 48
    zz = 49
    aaa = 50
    bbb = 51
    return a + b

def deeply_nested():
    if True:
        for i in range(10):
            while True:
                try:
                    if i > 5:
                        pass
                except Exception:
                    pass
                break

result = os.path.join("a", "b")
'''

    checker = PythonCodeChecker(sample_code)
    results = checker.check()

    print(results.summary())
    print(f"Total issues: {results.total_issues()}")
    print()

    if results.unused_imports:
        print("Unused Imports:")
        for r in results.unused_imports:
            print(f"  Line {r.line}: {r.message}")

    if results.unused_variables:
        print("Unused Variables:")
        for r in results.unused_variables:
            print(f"  Line {r.line}: {r.message} (scope: {r.scope})")

    if results.long_functions:
        print("Long Functions:")
        for r in results.long_functions:
            print(f"  Line {r.line}: {r.message}")

    if results.deep_nesting:
        print("Deep Nesting:")
        for r in results.deep_nesting:
            print(f"  Line {r.line}: {r.message}")
