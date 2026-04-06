import ast
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    """Represents a single code issue found by the checker."""
    category: str
    message: str
    line: int
    col: Optional[int] = None


@dataclass
class CheckResults:
    """Container for all issues found during code analysis."""
    unused_imports: List[Issue] = field(default_factory=list)
    unused_variables: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)

    @property
    def all_issues(self) -> List[Issue]:
        return (
            self.unused_imports
            + self.unused_variables
            + self.long_functions
            + self.deep_nesting
        )

    @property
    def total_count(self) -> int:
        return len(self.all_issues)


class _ImportVisitor(ast.NodeVisitor):
    """Collects all imported names (import X, from Y import X)."""

    def __init__(self):
        self.imported_names: set = set()
        self.import_nodes: list = []  # (name, node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # For 'import os.path', track 'os'
            top_name = name.split(".")[0]
            self.imported_names.add(top_name)
            self.import_nodes.append((top_name, node))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
            self.import_nodes.append((name, node))


class _ReferenceVisitor(ast.NodeVisitor):
    """Collects all name references (Name nodes) to check usage."""

    def __init__(self):
        self.references: set = set()
        self.names_by_scope: dict = {}  # name -> set of line numbers

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, (ast.Load, ast.Del)):
            self.references.add(node.id)
        self.names_by_scope.setdefault(node.id, set()).add(node.lineno)


class _AssignmentVisitor(ast.NodeVisitor):
    """Collects variable assignments and tracks their usage."""

    def __init__(self):
        self.assignments: dict = {}  # name -> {line, used: bool}
        self.references: set = set()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.references.add(node.id)

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            self._collect_targets(target, node.lineno)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            self.assignments.setdefault(name, {"line": node.lineno, "used": False})

    def _collect_targets(self, target, lineno: int):
        if isinstance(target, ast.Name):
            name = target.id
            if name not in ("_",):
                self.assignments.setdefault(name, {"line": lineno, "used": False})
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_targets(elt, lineno)

    def finalize(self):
        for name, info in self.assignments.items():
            if name in self.references:
                info["used"] = True


def check_code(source: str) -> CheckResults:
    """Check Python source code for common issues.

    Detects:
      - Unused imports (imported but never referenced)
      - Unused variables (assigned but never read)
      - Functions longer than 50 lines
      - Nesting deeper than 4 levels (if/for/while/with/try)

    Args:
        source: Python source code as string.

    Returns:
        CheckResults with all issues found.
    """
    results = CheckResults()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        # Can't analyze code with syntax errors
        return results

    # --- 1. Unused Imports ---
    import_visitor = _ImportVisitor()
    import_visitor.visit(tree)

    ref_visitor = _ReferenceVisitor()
    ref_visitor.visit(tree)

    for name, node in import_visitor.import_nodes:
        if name not in ref_visitor.references:
            results.unused_imports.append(
                Issue(
                    category="unused_import",
                    message=f"Import '{name}' is never used",
                    line=node.lineno,
                    col=node.col_offset,
                )
            )

    # --- 2. Unused Variables ---
    assign_visitor = _AssignmentVisitor()
    assign_visitor.visit(tree)
    assign_visitor.finalize()

    # Exclude common patterns that look unused but aren't
    dunder_names = {name for name in assign_visitor.assignments if name.startswith("__") and name.endswith("__")}
    builtin_constants = {"__name__", "__file__", "__doc__", "__all__", "__version__"}

    for name, info in assign_visitor.assignments.items():
        if not info["used"] and name not in builtin_constants and not name.startswith("_"):
            results.unused_variables.append(
                Issue(
                    category="unused_variable",
                    message=f"Variable '{name}' is assigned but never used",
                    line=info["line"],
                )
            )

    # --- 3. Functions longer than 50 lines ---
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start_line
            line_count = end_line - start_line + 1
            if line_count > 50:
                results.long_functions.append(
                    Issue(
                        category="long_function",
                        message=f"Function '{node.name}' is {line_count} lines long (max 50)",
                        line=start_line,
                    )
                )

    # --- 4. Deep nesting (> 4 levels) ---
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)

    def check_nesting(node: ast.AST, depth: int = 0):
        if depth > 4:
            results.deep_nesting.append(
                Issue(
                    category="deep_nesting",
                    message=f"Nesting depth {depth} exceeds 4",
                    line=node.lineno if hasattr(node, "lineno") else 0,
                )
            )
            return  # Don't report deeper levels for the same branch

        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                check_nesting(child, depth + 1)
            else:
                check_nesting(child, depth)

    for node in ast.walk(tree):
        if isinstance(node, nesting_nodes):
            check_nesting(node, 1)

    return results


if __name__ == "__main__":
    test_code = '''
import os
import sys
import json  # unused

def very_long_function():
    """This function is way too long."""
    x = 1
    y = 2
    z = 3
    a = 4
    b = 5
    c = 6
    d = 7
    e = 8
    f = 9
    g = 10
    h = 11
    i = 12
    j = 13
    k = 14
    l = 15
    m = 16
    n = 17
    o = 18
    p = 19
    q = 20
    r = 21
    s = 22
    t = 23
    u = 24
    v = 25
    w = 26
    x2 = 27
    y2 = 28
    z2 = 29
    a2 = 30
    b2 = 31
    c2 = 32
    d2 = 33
    e2 = 34
    f2 = 35
    g2 = 36
    h2 = 37
    i2 = 38
    j2 = 39
    k2 = 40
    l2 = 41
    m2 = 42
    n2 = 43
    o2 = 44
    p2 = 45
    q2 = 46
    r2 = 47
    s2 = 48
    t2 = 49
    u2 = 50
    v2 = 51
    return v2

def test_unused_vars():
    unused = 42
    also_unused = "hello"
    used = os.path.exists(".")
    return used

def deep_nesting_example():
    if True:
        for i in range(10):
            if i > 5:
                while True:
                    if True:
                        if True:
                            x = 1
    '''

    results = check_code(test_code)
    print(f"Total issues: {results.total_count}\n")

    for issue in results.unused_imports:
        print(f"[unused_import] Line {issue.line}: {issue.message}")
    for issue in results.unused_variables:
        print(f"[unused_variable] Line {issue.line}: {issue.message}")
    for issue in results.long_functions:
        print(f"[long_function] Line {issue.line}: {issue.message}")
    for issue in results.deep_nesting:
        print(f"[deep_nesting] Line {issue.line}: {issue.message}")
