import ast
from dataclasses import dataclass, field
from typing import List, Set, Dict


@dataclass
class Issue:
    type: str
    message: str
    line: int


@dataclass
class CheckResults:
    unused_imports: List[Issue] = field(default_factory=list)
    unused_variables: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)

    def all_issues(self) -> List[Issue]:
        return (
            self.unused_imports +
            self.unused_variables +
            self.long_functions +
            self.deep_nesting
        )


class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports: Dict[str, int] = {}  # name -> line
        self.import_usage: Dict[str, bool] = {}  # name -> used
        self.variables: Dict[str, int] = {}  # name -> line (first assignment)
        self.variable_usage: Dict[str, bool] = {}  # name -> used
        self.function_lines: List[tuple] = []  # (name, start_line, end_line)
        self.nesting_levels: List[tuple] = []  # (node_type, line, level)
        self.current_function = None
        self.function_start = None
        self.scope_stack: List[Set[str]] = [set()]  # Track variables per scope

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
            self.import_usage[name] = False
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
            self.import_usage[name] = False
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._check_function_length(node)
        self._check_nesting(node, 0)
        
        old_function = self.current_function
        old_start = self.function_start
        self.current_function = node.name
        self.function_start = node.lineno
        
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop()
        
        self.current_function = old_function
        self.function_start = old_start

    def visit_AsyncFunctionDef(self, node):
        self._check_function_length(node)
        self._check_nesting(node, 0)
        
        old_function = self.current_function
        old_start = self.function_start
        self.current_function = node.name
        self.function_start = node.lineno
        
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop()
        
        self.current_function = old_function
        self.function_start = old_start

    def _check_function_length(self, node):
        if hasattr(node, 'body') and node.body:
            start_line = node.lineno
            end_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else start_line
            if end_line:
                line_count = end_line - start_line + 1
                if line_count > 50:
                    self.function_lines.append((node.name, start_line, line_count))

    def _check_nesting(self, node, current_level):
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
        
        def count_nesting(node, level):
            if isinstance(node, nesting_nodes):
                level += 1
                if level > 4:
                    self.nesting_levels.append((type(node).__name__, node.lineno, level))
            
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                count_nesting(child, level)
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            count_nesting(child, current_level)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            # Variable assignment
            if node.id not in self.variables:
                self.variables[node.id] = node.lineno
                self.variable_usage[node.id] = False
            self.scope_stack[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Variable usage
            if node.id in self.imports:
                self.import_usage[node.id] = True
            if node.id in self.variables:
                self.variable_usage[node.id] = True
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Handle module usage like `os.path.join`
        if isinstance(node.value, ast.Name):
            if node.value.id in self.imports:
                self.import_usage[node.value.id] = True
        self.generic_visit(node)


def check_code(source: str) -> CheckResults:
    """
    Analyze Python source code and return check results.
    
    Detects:
    - Unused imports (imported but never referenced)
    - Unused variables (assigned but never read)
    - Functions longer than 50 lines
    - Nesting deeper than 4 levels (if/for/while/with/try)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        results.unused_imports.append(Issue("syntax_error", f"Syntax error: {e}", e.lineno if e.lineno else 0))
        return results

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)

    results = CheckResults()

    # Check unused imports
    for name, line in analyzer.imports.items():
        if not analyzer.import_usage.get(name, True):
            results.unused_imports.append(Issue("unused_import", f"Unused import: '{name}'", line))

    # Check unused variables
    # Filter out special variables and those used in other scopes
    special_vars = {'_', 'self', 'cls'}
    for name, line in analyzer.variables.items():
        if name not in special_vars and not analyzer.variable_usage.get(name, True):
            results.unused_variables.append(Issue("unused_variable", f"Unused variable: '{name}'", line))

    # Check long functions
    for func_name, line, line_count in analyzer.function_lines:
        results.long_functions.append(
            Issue("long_function", f"Function '{func_name}' is {line_count} lines (max 50)", line)
        )

    # Check deep nesting
    for node_type, line, level in analyzer.nesting_levels:
        results.deep_nesting.append(
            Issue("deep_nesting", f"{node_type} at nesting level {level} (max 4)", line)
        )

    return results


if __name__ == "__main__":
    # Test code with various issues
    test_code = '''
import os
import sys  # unused
import json

def long_function():
    """This function is too long."""
    x = 1
    y = 2  # unused
    z = 3
    
    if x > 0:
        if z > 0:
            if x < 10:
                if z < 10:
                    print("Deep nesting!")
    
    # Padding to make function long
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
    x1 = 24
    y1 = 25
    z1 = 26
    a1 = 27
    b1 = 28
    c1 = 29
    d1 = 30
    e1 = 31
    f1 = 32
    g1 = 33
    h1 = 34
    i1 = 35
    j1 = 36
    k1 = 37
    l1 = 38
    m1 = 39
    n1 = 40
    o1 = 41
    p1 = 42
    q1 = 43
    r1 = 44
    s1 = 45
    t1 = 46
    u1 = 47
    v1 = 48
    w1 = 49
    x2 = 50
    y2 = 51
    z2 = 52
    
    return x

def good_function():
    """This function is fine."""
    data = json.dumps({"key": "value"})
    return data
'''

    results = check_code(test_code)

    print("=== Code Check Results ===\n")

    print(f"Unused Imports ({len(results.unused_imports)}):")
    for issue in results.unused_imports:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nUnused Variables ({len(results.unused_variables)}):")
    for issue in results.unused_variables:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nLong Functions ({len(results.long_functions)}):")
    for issue in results.long_functions:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nDeep Nesting ({len(results.deep_nesting)}):")
    for issue in results.deep_nesting:
        print(f"  Line {issue.line}: {issue.message}")

    print(f"\nTotal issues found: {len(results.all_issues())}")
