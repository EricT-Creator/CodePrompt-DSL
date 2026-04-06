import ast
from dataclasses import dataclass, field
from typing import List, Set, Dict

@dataclass
class CheckResults:
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[Dict[str, any]] = field(default_factory=list)
    deep_nesting: List[Dict[str, any]] = field(default_factory=list)

class CodeChecker(ast.NodeVisitor):
    def __init__(self):
        self.imports: Dict[str, ast.AST] = {}
        self.import_aliases: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        self.assigned_names: Dict[str, ast.AST] = {}
        self.used_assignments: Set[str] = set()
        self.functions: List[Dict[str, any]] = []
        self.current_function: str = None
        self.function_lines: Dict[str, int] = {}
        self.nesting_depth: int = 0
        self.max_nesting: Dict[str, int] = {}
        self.deep_nesting_locations: List[Dict[str, any]] = []
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
            if node.id in self.assigned_names:
                self.used_assignments.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.assigned_names[node.id] = node
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function = self.current_function
        old_nesting = self.nesting_depth
        
        self.current_function = node.name
        end_line = getattr(node, 'end_lineno', node.lineno)
        start_line = node.lineno
        line_count = end_line - start_line + 1 if end_line else 1
        self.function_lines[node.name] = line_count
        
        self.nesting_depth = 1
        self.max_nesting[node.name] = 1
        
        for item in node.body:
            self.visit(item)
        
        if self.max_nesting[node.name] > 4:
            self.deep_nesting_locations.append({
                'function': node.name,
                'line': node.lineno,
                'max_depth': self.max_nesting[node.name]
            })
        
        self.current_function = old_function
        self.nesting_depth = old_nesting
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)
    
    def visit_If(self, node: ast.If):
        self._visit_nested(node)
    
    def visit_For(self, node: ast.For):
        self._visit_nested(node)
    
    def visit_While(self, node: ast.While):
        self._visit_nested(node)
    
    def visit_With(self, node: ast.With):
        self._visit_nested(node)
    
    def visit_Try(self, node: ast.Try):
        self._visit_nested(node)
    
    def _visit_nested(self, node):
        if self.current_function:
            self.nesting_depth += 1
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 1),
                self.nesting_depth
            )
        
        self.generic_visit(node)
        
        if self.current_function:
            self.nesting_depth -= 1
    
    def get_results(self) -> CheckResults:
        unused_imports = [
            name for name in self.imports.keys() 
            if name not in self.used_names
        ]
        
        unused_variables = [
            name for name in self.assigned_names.keys()
            if name not in self.used_assignments and not name.startswith('_')
        ]
        
        long_functions = [
            {'name': name, 'lines': lines}
            for name, lines in self.function_lines.items()
            if lines > 50
        ]
        
        return CheckResults(
            unused_imports=unused_imports,
            unused_variables=unused_variables,
            long_functions=long_functions,
            deep_nesting=self.deep_nesting_locations
        )


def check_code(source: str) -> CheckResults:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python code: {e}")
    
    checker = CodeChecker()
    checker.visit(tree)
    return checker.get_results()


if __name__ == "__main__":
    test_code = '''
import os
import sys
import json

unused_var = 42
used_var = 100

def long_function():
    x = 1
    x = 2
    x = 3
    if x > 0:
        if x > 1:
            if x > 2:
                if x > 3:
                    if x > 4:
                        print("deep")
    return x

def short_func():
    print(used_var)
'''
    
    results = check_code(test_code)
    print("未使用的导入:", results.unused_imports)
    print("未使用的变量:", results.unused_variables)
    print("超过50行的函数:", results.long_functions)
    print("超过4层嵌套:", results.deep_nesting)
