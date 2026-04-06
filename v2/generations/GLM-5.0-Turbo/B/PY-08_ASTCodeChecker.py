import ast
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    type: str
    message: str
    line: int
    col: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "message": self.message,
            "line": self.line,
            "col": self.col,
        }


@dataclass
class CheckResults:
    unused_imports: List[Issue] = field(default_factory=list)
    unused_variables: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.unused_imports) + len(self.unused_variables) + \
               len(self.long_functions) + len(self.deep_nesting)

    @property
    def has_issues(self) -> bool:
        return self.total_issues > 0

    def summary(self) -> str:
        parts = []
        if self.unused_imports:
            parts.append(f"{len(self.unused_imports)} unused import(s)")
        if self.unused_variables:
            parts.append(f"{len(self.unused_variables)} unused variable(s)")
        if self.long_functions:
            parts.append(f"{len(self.long_functions)} long function(s) >50 lines")
        if self.deep_nesting:
            parts.append(f"{len(self.deep_nesting)} deep nesting(s) >4 levels")
        if not parts:
            return "No issues found."
        return ", ".join(parts) + f" ({self.total_issues} total)"

    def to_dict(self) -> dict:
        return {
            "total_issues": self.total_issues,
            "unused_imports": [i.to_dict() for i in self.unused_imports],
            "unused_variables": [i.to_dict() for i in self.unused_variables],
            "long_functions": [i.to_dict() for i in self.long_functions],
            "deep_nesting": [i.to_dict() for i in self.deep_nesting],
        }


class CodeChecker(ast.NodeVisitor):
    """AST-based code checker that detects common code quality issues.

    Detects:
    - Unused imports
    - Unused variables (function-level)
    - Functions longer than 50 lines
    - Nesting deeper than 4 levels
    """

    MAX_FUNCTION_LINES = 50
    MAX_NESTING_LEVEL = 4

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.results = CheckResults()

        # Track imports: name -> line
        self.imports: dict[str, int] = {}
        self.import_aliases: dict[str, str] = {}  # alias -> original name

        # Track function-level variable usage
        self.scope_stack: list[dict[str, bool]] = []
        self.all_names_used: set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # For "import os.path", use the first part
            base_name = name.split(".")[0]
            self.imports[base_name] = node.lineno
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
        self.generic_visit(node)

    def visit_Name(self, node: ast.Node):
        if isinstance(node.ctx, (ast.Load, ast.Del)):
            self.all_names_used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Track module.attribute usage (e.g., os.path.join -> mark os as used)
        if isinstance(node.value, ast.Name):
            self.all_names_used.add(node.value.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        # Check function length
        func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') and node.end_lineno else 0
        if func_lines > self.MAX_FUNCTION_LINES:
            self.results.long_functions.append(Issue(
                type="long_function",
                message=f"Function '{node.name}' is {func_lines} lines (max {self.MAX_FUNCTION_LINES})",
                line=node.lineno,
            ))

        # Track function-level variables for unused variable detection
        local_vars: dict[str, int] = {}
        used_in_scope: set[str] = set()

        # Collect assigned names in this function
        self._collect_assignments(node, local_vars)

        # Collect names used in this function
        self._collect_usage(node, used_in_scope)

        # Mark imports used inside this function
        self.all_names_used.update(used_in_scope)

        # Find unused local variables (excluding _ prefix convention)
        for var_name, var_line in local_vars.items():
            if var_name.startswith("_"):
                continue
            if var_name not in used_in_scope and var_name not in self.imports:
                self.results.unused_variables.append(Issue(
                    type="unused_variable",
                    message=f"Variable '{var_name}' is assigned but never used",
                    line=var_line,
                ))

        # Check nesting depth
        self._check_nesting(node, 0)

        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _collect_assignments(self, node: ast.AST, assignments: dict[str, int]):
        """Collect all variable assignments in a function body."""
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        assignments[target.id] = target.lineno
            elif isinstance(child, ast.AnnAssign) and child.target:
                if isinstance(child.target, ast.Name):
                    assignments[child.target.id] = child.target.lineno
            elif isinstance(child, (ast.For, ast.AsyncFor)):
                if isinstance(child.target, ast.Name):
                    assignments[child.target.id] = child.target.lineno
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                for item in child.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        assignments[item.optional_vars.id] = item.optional_vars.lineno

    def _collect_usage(self, node: ast.AST, used: set[str]):
        """Collect all names that are read/used in a node."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                used.add(child.id)

    def _check_nesting(self, node: ast.AST, depth: int):
        """Check for nesting deeper than MAX_NESTING_LEVEL."""
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)

        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                new_depth = depth + 1
                if new_depth > self.MAX_NESTING_LEVEL:
                    self.results.deep_nesting.append(Issue(
                        type="deep_nesting",
                        message=f"Nesting depth {new_depth} exceeds maximum {self.MAX_NESTING_LEVEL}",
                        line=child.lineno,
                    ))
                self._check_nesting(child, new_depth)
            else:
                self._check_nesting(child, depth)

    def finalize(self) -> CheckResults:
        """Check for unused imports after full traversal."""
        for name, line in self.imports.items():
            if name not in self.all_names_used:
                self.results.unused_imports.append(Issue(
                    type="unused_import",
                    message=f"Import '{name}' is never used",
                    line=line,
                ))
        return self.results


def check_code(source: str) -> CheckResults:
    """Check Python source code for common issues.

    Args:
        source: Python source code string

    Returns:
        CheckResults dataclass with all detected issues
    """
    source_lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.unused_variables.append(Issue(
            type="syntax_error",
            message=f"Syntax error: {e.msg}",
            line=e.lineno or 0,
            col=e.offset,
        ))
        return results

    checker = CodeChecker(source_lines)
    checker.visit(tree)
    return checker.finalize()


if __name__ == "__main__":
    # Example usage
    sample_code = '''
import os
import json
import sys
from collections import defaultdict

unused_var = 42

def very_long_function():
    """This function is intentionally very long."""
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
    xx = 27
    yy = 28
    zz = 29
    aa = 30
    bb = 31
    cc = 32
    dd = 33
    ee = 34
    ff = 35
    gg = 36
    hh = 37
    ii = 38
    jj = 39
    kk = 40
    ll = 41
    mm = 42
    nn = 43
    oo = 44
    pp = 45
    qq = 46
    rr = 47
    ss = 48
    tt = 49
    uu = 50
    vv = 51
    ww = 52
    return ww

def deep_nesting_example(data):
    if data:
        for item in data:
            if item:
                with open("test") as f:
                    for line in f:
                        if True:
                            try:
                                pass
                            except Exception:
                                pass
    return data
'''

    results = check_code(sample_code)
    print(f"=== Code Check Results ===")
    print(f"Summary: {results.summary()}")
    print()
    for issue in results.unused_imports:
        print(f"  [unused_import] Line {issue.line}: {issue.message}")
    for issue in results.unused_variables:
        print(f"  [unused_variable] Line {issue.line}: {issue.message}")
    for issue in results.long_functions:
        print(f"  [long_function] Line {issue.line}: {issue.message}")
    for issue in results.deep_nesting:
        print(f"  [deep_nesting] Line {issue.line}: {issue.message}")
