"""AST Code Checker — Python 3.10+ standard library only."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


# ─── Result Dataclasses ───────────────────────────────────────


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
    unused_imports: list[UnusedImportIssue]
    unused_variables: list[UnusedVariableIssue]
    long_functions: list[LongFunctionIssue]
    deep_nesting: list[DeepNestingIssue]
    total_issues: int
    source_lines: int


# ─── AST Visitors ─────────────────────────────────────────────


class ImportCollector(ast.NodeVisitor):
    """Collects all imported names and their line numbers."""

    def __init__(self) -> None:
        self.imports: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                "name": alias.asname or alias.name,
                "original": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "module": None,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                self.imports.append({
                    "name": "*",
                    "original": "*",
                    "alias": None,
                    "line": node.lineno,
                    "module": module,
                })
            else:
                self.imports.append({
                    "name": alias.asname or alias.name,
                    "original": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "module": module,
                })
        self.generic_visit(node)


class NameUsageCollector(ast.NodeVisitor):
    """Collects all name references (loads) in non-import contexts."""

    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Capture the root name for module.func patterns
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            self.used_names.add(root.id)
        self.generic_visit(node)


class VariableTracker(ast.NodeVisitor):
    """Tracks variable assignments and usages per scope."""

    def __init__(self) -> None:
        self.issues: list[UnusedVariableIssue] = []
        self._scope_stack: list[dict[str, dict[str, Any]]] = [{}]  # module scope
        self._scope_names: list[str] = ["<module>"]

    def _current_scope(self) -> dict[str, dict[str, Any]]:
        return self._scope_stack[-1]

    def _mark_assigned(self, name: str, line: int) -> None:
        scope = self._current_scope()
        if name not in scope:
            scope[name] = {"assigned": True, "used": False, "line": line}
        else:
            scope[name]["assigned"] = True
            if scope[name]["line"] == 0:
                scope[name]["line"] = line

    def _mark_used(self, name: str) -> None:
        # Look up through scope stack
        for scope in reversed(self._scope_stack):
            if name in scope:
                scope[name]["used"] = True
                return

    def _push_scope(self, name: str) -> None:
        self._scope_stack.append({})
        self._scope_names.append(name)

    def _pop_scope(self) -> None:
        scope = self._scope_stack.pop()
        scope_name = self._scope_names.pop()

        for var_name, info in scope.items():
            if info["assigned"] and not info["used"]:
                # Skip conventionally ignored names
                if var_name.startswith("_"):
                    continue
                self.issues.append(
                    UnusedVariableIssue(
                        name=var_name,
                        line=info["line"],
                        scope=scope_name,
                    )
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope(node.name)
        # Register parameters as assigned
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

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._push_scope(node.name)
        self.generic_visit(node)
        self._pop_scope()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._mark_assigned(node.id, node.lineno)
        elif isinstance(node.ctx, ast.Load):
            self._mark_used(node.id)
        self.generic_visit(node)


class FunctionAnalyzer(ast.NodeVisitor):
    """Visits function definitions to calculate line count and nesting depth."""

    NESTING_TYPES = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
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
        # Check length
        end_line = getattr(node, "end_lineno", None)
        if end_line is not None:
            length = end_line - node.lineno + 1
            if length > 50:
                self.long_functions.append(
                    LongFunctionIssue(
                        function_name=node.name,
                        line=node.lineno,
                        length=length,
                        threshold=50,
                    )
                )

        # Check nesting depth
        max_depth = self._compute_max_depth(node, current_depth=0)
        if max_depth > 4:
            self.deep_nesting.append(
                DeepNestingIssue(
                    function_name=node.name,
                    line=node.lineno,
                    max_depth=max_depth,
                    threshold=4,
                )
            )

    def _compute_max_depth(self, node: ast.AST, current_depth: int) -> int:
        max_d = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.NESTING_TYPES):
                child_max = self._compute_max_depth(child, current_depth + 1)
                if child_max > max_d:
                    max_d = child_max
            else:
                child_max = self._compute_max_depth(child, current_depth)
                if child_max > max_d:
                    max_d = child_max

        return max_d


# ─── Code Checker ─────────────────────────────────────────────


class CodeChecker:
    """Python code checker that performs four checks using AST analysis."""

    def check(self, source: str) -> CheckResult:
        """Parse source, run all checks, aggregate results."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return CheckResult(
                unused_imports=[],
                unused_variables=[],
                long_functions=[],
                deep_nesting=[],
                total_issues=0,
                source_lines=source.count("\n") + 1,
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
        """Check for unused imports."""
        import_collector = ImportCollector()
        import_collector.visit(tree)

        usage_collector = NameUsageCollector()
        usage_collector.visit(tree)

        used = usage_collector.used_names
        issues: list[UnusedImportIssue] = []

        for imp in import_collector.imports:
            name = imp["name"]
            if name == "*":
                continue
            if name.startswith("_"):
                continue
            if name not in used:
                issues.append(
                    UnusedImportIssue(
                        name=name,
                        line=imp["line"],
                        module=imp["module"],
                    )
                )

        return issues

    def check_unused_variables(self, tree: ast.Module) -> list[UnusedVariableIssue]:
        """Check for unused variables."""
        tracker = VariableTracker()
        tracker.visit(tree)
        # Also check module scope
        scope = tracker._scope_stack[0]
        scope_name = tracker._scope_names[0]
        for var_name, info in scope.items():
            if info["assigned"] and not info["used"]:
                if var_name.startswith("_"):
                    continue
                tracker.issues.append(
                    UnusedVariableIssue(
                        name=var_name,
                        line=info["line"],
                        scope=scope_name,
                    )
                )
        return tracker.issues

    def check_long_functions(self, tree: ast.Module) -> list[LongFunctionIssue]:
        """Check for functions longer than 50 lines."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.long_functions

    def check_deep_nesting(self, tree: ast.Module) -> list[DeepNestingIssue]:
        """Check for nesting depth exceeding 4 levels."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.deep_nesting


# ─── Main (demonstration) ────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from pathlib import Path

def short_func():
    x = 1
    return x

def unused_var_func():
    a = 10
    b = 20
    return a

def deeply_nested():
    for i in range(10):
        if i > 0:
            for j in range(5):
                if j > 0:
                    while True:
                        if j == 3:
                            break
                        break

def long_function():
    """This function is artificially long."""
    x = 1
    y = 2
    z = 3
    a = x + y
    b = y + z
    c = a + b
    d = c + 1
    e = d + 1
    f = e + 1
    g = f + 1
    h = g + 1
    i = h + 1
    j = i + 1
    k = j + 1
    l = k + 1
    m = l + 1
    n = m + 1
    o = n + 1
    p = o + 1
    q = p + 1
    r = q + 1
    s = r + 1
    t = s + 1
    u = t + 1
    v = u + 1
    w = v + 1
    x2 = w + 1
    y2 = x2 + 1
    z2 = y2 + 1
    aa = z2 + 1
    bb = aa + 1
    cc = bb + 1
    dd = cc + 1
    ee = dd + 1
    ff = ee + 1
    gg = ff + 1
    hh = gg + 1
    ii = hh + 1
    jj = ii + 1
    kk = jj + 1
    ll = kk + 1
    mm = ll + 1
    nn = mm + 1
    oo = nn + 1
    pp = oo + 1
    qq = pp + 1
    rr = qq + 1
    ss = rr + 1
    tt = ss + 1
    uu = tt + 1
    vv = uu + 1
    ww = vv + 1
    xx = ww + 1
    yy = xx + 1
    zz = yy + 1
    return zz

result = long_function()
print(result)
'''

    checker = CodeChecker()
    result = checker.check(sample_code)

    print(f"Source lines: {result.source_lines}")
    print(f"Total issues: {result.total_issues}")
    print()

    if result.unused_imports:
        print("Unused imports:")
        for issue in result.unused_imports:
            print(f"  Line {issue.line}: {issue.name}" + (f" (from {issue.module})" if issue.module else ""))

    if result.unused_variables:
        print("Unused variables:")
        for issue in result.unused_variables:
            print(f"  Line {issue.line}: {issue.name} in {issue.scope}")

    if result.long_functions:
        print("Long functions (>{} lines):".format(result.long_functions[0].threshold))
        for issue in result.long_functions:
            print(f"  Line {issue.line}: {issue.function_name} ({issue.length} lines)")

    if result.deep_nesting:
        print("Deep nesting (>{} levels):".format(result.deep_nesting[0].threshold))
        for issue in result.deep_nesting:
            print(f"  Line {issue.line}: {issue.function_name} (depth {issue.max_depth})")
