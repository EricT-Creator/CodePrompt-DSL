import ast
from dataclasses import dataclass, field
from typing import List, Set, Dict
from collections import defaultdict


@dataclass
class CheckResults:
    """Results from AST code analysis."""
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[Dict] = field(default_factory=list)
    deeply_nested: List[Dict] = field(default_factory=list)


class CodeChecker(ast.NodeVisitor):
    """
    AST-based code checker using NodeVisitor.
    Detects:
    - Unused imports
    - Unused variables
    - Functions > 50 lines
    - Nesting > 4 levels
    """
    
    def __init__(self):
        self.results = CheckResults()
        
        # Track imports and their usage
        self.imports: Dict[str, str] = {}  # name -> alias/original
        self.import_usages: Set[str] = set()
        
        # Track variable assignments and usages
        self.current_scope_vars: Dict[str, Set[str]] = defaultdict(set)  # scope -> vars
        self.current_scope_usages: Dict[str, Set[str]] = defaultdict(set)
        self.scope_stack: List[str] = ['global']
        
        # Track function info
        self.current_function: str = None
        self.function_lines: Dict[str, int] = {}
        self.function_start_lines: Dict[str, int] = {}
        
        # Track nesting depth
        self.nesting_level = 0
        self.max_nesting = 4
        self.deeply_nested_locations: List[Dict] = []
    
    def visit_Import(self, node: ast.Import):
        """Track regular imports."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        module = node.module or ''
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = f"{module}.{alias.name}" if module else alias.name
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Track name usages."""
        if isinstance(node.ctx, ast.Load):
            name = node.id
            # Check if it's an import usage
            if name in self.imports:
                self.import_usages.add(name)
            # Track variable usage in current scope
            self.current_scope_usages[self.scope_stack[-1]].add(name)
        elif isinstance(node.ctx, ast.Store):
            # Track variable assignment
            self.current_scope_vars[self.scope_stack[-1]].add(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function definitions."""
        func_name = node.name
        self.function_start_lines[func_name] = node.lineno
        
        # Calculate function length
        if hasattr(node, 'end_lineno') and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                self.results.long_functions.append({
                    'name': func_name,
                    'lines': length,
                    'start_line': node.lineno
                })
        
        # Enter new scope
        prev_function = self.current_function
        self.current_function = func_name
        self.scope_stack.append(func_name)
        
        # Track nesting
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'function',
                'name': func_name,
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        
        self.generic_visit(node)
        
        # Exit scope
        self.nesting_level -= 1
        self.scope_stack.pop()
        self.current_function = prev_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Handle async functions same as regular functions."""
        self.visit_FunctionDef(node)  # Reuse logic
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class definitions for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'class',
                'name': node.name,
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        
        self.scope_stack.append(f"class:{node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()
        self.nesting_level -= 1
    
    def visit_If(self, node: ast.If):
        """Track if statements for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'if',
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_For(self, node: ast.For):
        """Track for loops for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'for',
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node: ast.While):
        """Track while loops for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'while',
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_With(self, node: ast.With):
        """Track with statements for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'with',
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_Try(self, node: ast.Try):
        """Track try blocks for nesting."""
        self.nesting_level += 1
        if self.nesting_level > self.max_nesting:
            self.deeply_nested_locations.append({
                'type': 'try',
                'line': node.lineno,
                'nesting_level': self.nesting_level
            })
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def finalize(self):
        """Finalize results after visiting all nodes."""
        # Find unused imports
        for name in self.imports:
            if name not in self.import_usages:
                self.results.unused_imports.append(name)
        
        # Find unused variables (per scope)
        all_assigned = set()
        all_used = set()
        for scope in self.current_scope_vars:
            all_assigned.update(self.current_scope_vars[scope])
        for scope in self.current_scope_usages:
            all_used.update(self.current_scope_usages[scope])
        
        # Variables assigned but never used (excluding special names)
        special_names = {'_', 'self', 'cls'}
        for var in all_assigned - all_used:
            if var not in special_names and not var.startswith('_'):
                self.results.unused_variables.append(var)
        
        # Remove duplicates from deeply nested
        seen = set()
        unique_nested = []
        for item in self.deeply_nested_locations:
            key = (item.get('type'), item.get('name', ''), item.get('line'))
            if key not in seen:
                seen.add(key)
                unique_nested.append(item)
        self.results.deeply_nested = unique_nested


def check_code(source: str) -> CheckResults:
    """
    Check Python source code for various issues.
    
    Args:
        source: Python source code string
    
    Returns:
        CheckResults dataclass with findings
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results = CheckResults()
        # Return empty results for syntax errors
        return results
    
    checker = CodeChecker()
    checker.visit(tree)
    checker.finalize()
    
    return checker.results


def main():
    """Example usage of AST code checker."""
    
    # Example code with various issues
    example_code = '''
import os
import sys
import json  # unused
from typing import List, Dict  # Dict unused

def short_function():
    x = 1  # unused variable
    y = 2
    return y

def very_long_function():
    """This function has more than 50 lines."""
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
    zz = 52
    return a + zz

def deeply_nested_function():
    if True:
        if True:
            if True:
                if True:
                    if True:  # 5 levels deep
                        print("too nested")
'''
    
    print("Checking code...\n")
    results = check_code(example_code)
    
    print("Results:")
    print("=" * 50)
    
    print(f"\n1. Unused Imports ({len(results.unused_imports)}):")
    for imp in results.unused_imports:
        print(f"   - {imp}")
    
    print(f"\n2. Unused Variables ({len(results.unused_variables)}):")
    for var in results.unused_variables:
        print(f"   - {var}")
    
    print(f"\n3. Long Functions ({len(results.long_functions)}):")
    for func in results.long_functions:
        print(f"   - {func['name']}: {func['lines']} lines (line {func['start_line']})")
    
    print(f"\n4. Deep Nesting ({len(results.deeply_nested)}):")
    for item in results.deeply_nested:
        if 'name' in item:
            print(f"   - {item['type']} '{item['name']}' at line {item['line']} ({item['nesting_level']} levels)")
        else:
            print(f"   - {item['type']} at line {item['line']} ({item['nesting_level']} levels)")


if __name__ == "__main__":
    main()
