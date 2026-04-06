import ast
from dataclasses import dataclass
from typing import List

@dataclass
class CheckResults:
    unused_imports: List[str]
    unused_vars: List[str]
    long_funcs: List[str]
    deep_nesting: List[str]

class Checker(ast.NodeVisitor):
    def __init__(self):
        self.results = CheckResults([], [], [], [])

    def visit_FunctionDef(self, node):
        if len(node.body) > 50:
            self.results.long_funcs.append(node.name)
        self.generic_visit(node)

def check_code(source: str):
    tree = ast.parse(source)
    checker = Checker()
    checker.visit(tree)
    return checker.results

# Simplified example implementation
