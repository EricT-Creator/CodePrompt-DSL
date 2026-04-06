import ast
from dataclasses import dataclass

@dataclass
class CheckResults:
    unused_imports: list
    unused_vars: list
    long_functions: list
    deep_nesting: list

class ASTCodeChecker(ast.NodeVisitor):
    def __init__(self):
        self.results = CheckResults([], [], [], [])
        self.variables = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.results.unused_imports.append(alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if len(node.body) > 50:
            self.results.long_functions.append(node.name)
        self.generic_visit(node)

    def check_code(self, source):
        tree = ast.parse(source)
        self.visit(tree)
        return self.results

def check_code(source):
    return ASTCodeChecker().check_code(source)
