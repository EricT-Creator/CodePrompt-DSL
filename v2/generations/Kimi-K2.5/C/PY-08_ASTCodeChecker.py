import ast
from dataclasses import dataclass, field
from typing import List, Set, Dict


@dataclass
class CheckResults:
    """Results from code analysis."""
    unused_imports: List[str] = field(default_factory=list)
    unused_vars: List[str] = field(default_factory=list)
    long_functions: List[Dict] = field(default_factory=list)
    deeply_nested: List[Dict] = field(default_factory=list)


class CodeAnalyzer(ast.NodeVisitor):
    """AST-based code analyzer using NodeVisitor pattern."""
    
    def __init__(self):
        self.imports: Dict[str, ast.AST] = {}
        self.import_aliases: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        self.defined_vars: Dict[str, ast.AST] = {}
        self.used_vars: Set[str] = set()
        self.function_lines: List[Dict] = []
        self.deeply_nested: List[Dict] = []
        self.current_function: str = None
        self.current_function_start: int = 0
        self.nesting_stack: List[str] = []
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
            if alias.asname:
                self.import_aliases[alias.asname] = f"{module}.{alias.name}"
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
            self.used_vars.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_vars[node.id] = node
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        prev_function = self.current_function
        prev_start = self.current_function_start
        prev_stack = self.nesting_stack
        
        self.current_function = node.name
        self.current_function_start = node.lineno
        self.nesting_stack = []
        
        # Calculate function length
        end_line = getattr(node, 'end_lineno', node.lineno)
        if end_line:
            line_count = end_line - node.lineno + 1
            if line_count > 50:
                self.function_lines.append({
                    'name': node.name,
                    'lines': line_count,
                    'start_line': node.lineno
                })
        
        # Visit function body
        for item in node.body:
            self._check_nesting(item, 1)
        
        self.current_function = prev_function
        self.current_function_start = prev_start
        self.nesting_stack = prev_stack
    
    def _check_nesting(self, node, depth):
        if depth > 4:
            self.deeply_nested.append({
                'function': self.current_function,
                'depth': depth,
                'line': getattr(node, 'lineno', 0),
                'type': type(node).__name__
            })
        
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, 
                        ast.ExceptHandler, ast.AsyncFor, ast.AsyncWith)
        
        if isinstance(node, nesting_nodes):
            new_depth = depth + 1
        else:
            new_depth = depth
        
        for child in ast.iter_child_nodes(node):
            self._check_nesting(child, new_depth)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        # Visit class body but don't count class as function
        for item in node.body:
            self.visit(item)


def check_code(source: str) -> CheckResults:
    """
    Check Python source code for various issues.
    
    Args:
        source: Python source code as string
        
    Returns:
        CheckResults dataclass with findings
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python syntax: {e}")
    
    analyzer = CodeAnalyzer()
    analyzer.visit(tree)
    
    results = CheckResults()
    
    # Find unused imports
    for name in analyzer.imports:
        if name not in analyzer.used_names:
            results.unused_imports.append(name)
    
    # Find unused variables (excluding imports and special names)
    builtin_names = {'True', 'False', 'None', 'print', 'len', 'range', 'enumerate',
                     'zip', 'map', 'filter', 'sum', 'min', 'max', 'abs', 'round',
                     'int', 'str', 'float', 'list', 'dict', 'set', 'tuple'}
    
    for name in analyzer.defined_vars:
        if name not in analyzer.used_vars and name not in builtin_names:
            if name not in analyzer.imports:
                results.unused_vars.append(name)
    
    # Long functions
    results.long_functions = analyzer.function_lines
    
    # Deeply nested blocks
    results.deeply_nested = analyzer.deeply_nested
    
    return results


def main():
    """Example usage of AST code checker."""
    
    # Example code with various issues
    test_code = '''
import os
import sys
import json  # unused
from typing import List, Dict, Optional  # Optional unused

def short_function():
    x = 10
    y = 20  # unused
    return x

def very_long_function():
    """This function has more than 50 lines."""
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    line7 = 7
    line8 = 8
    line9 = 9
    line10 = 10
    line11 = 11
    line12 = 12
    line13 = 13
    line14 = 14
    line15 = 15
    line16 = 16
    line17 = 17
    line18 = 18
    line19 = 19
    line20 = 20
    line21 = 21
    line22 = 22
    line23 = 23
    line24 = 24
    line25 = 25
    line26 = 26
    line27 = 27
    line28 = 28
    line29 = 29
    line30 = 30
    line31 = 31
    line32 = 32
    line33 = 33
    line34 = 34
    line35 = 35
    line36 = 36
    line37 = 37
    line38 = 38
    line39 = 39
    line40 = 40
    line41 = 41
    line42 = 42
    line43 = 43
    line44 = 44
    line45 = 45
    line46 = 46
    line47 = 47
    line48 = 48
    line49 = 49
    line50 = 50
    line51 = 51
    line52 = 52
    return line1

def deeply_nested_function():
    if True:
        for i in range(10):
            if i > 5:
                while i < 10:
                    if i == 7:
                        print("deep nesting!")
                    i += 1

class MyClass:
    def method(self):
        unused_var = 100
        return 42
'''
    
    print("Analyzing code...")
    print("=" * 60)
    
    results = check_code(test_code)
    
    print(f"\nUnused imports ({len(results.unused_imports)}):")
    for imp in results.unused_imports:
        print(f"  - {imp}")
    
    print(f"\nUnused variables ({len(results.unused_vars)}):")
    for var in results.unused_vars:
        print(f"  - {var}")
    
    print(f"\nLong functions ({len(results.long_functions)}):")
    for func in results.long_functions:
        print(f"  - {func['name']}: {func['lines']} lines (line {func['start_line']})")
    
    print(f"\nDeeply nested blocks ({len(results.deeply_nested)}):")
    for nest in results.deeply_nested:
        print(f"  - {nest['function']}: depth {nest['depth']} at line {nest['line']} ({nest['type']})")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")


if __name__ == "__main__":
    main()
