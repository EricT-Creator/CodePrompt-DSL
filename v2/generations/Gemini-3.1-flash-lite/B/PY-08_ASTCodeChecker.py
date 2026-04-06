import ast
from dataclasses import dataclass

@dataclass
class CheckResults:
    unused_imports: list
    unused_vars: list
    long_functions: list
    complex_nesting: list

class ASTCodeChecker(ast.NodeVisitor):
    def __init__(self):
        self.results = CheckResults([], [], [], [])

    def visit_Import(self, node):
        for alias in node.names: self.results.unused_imports.append(alias.name)

    def visit_FunctionDef(self, node):
        if (node.end_lineno - node.lineno) > 50: self.results.long_functions.append(node.name)
        self.generic_visit(node)

def check_code(source):
    tree = ast.parse(source)
    checker = ASTCodeChecker()
    checker.visit(tree)
    return checker.results
