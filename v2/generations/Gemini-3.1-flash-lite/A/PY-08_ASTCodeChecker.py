import ast
from dataclasses import dataclass, field
from typing import List

@dataclass
class CheckResults:
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[str] = field(default_factory=list)
    deep_nesting: List[str] = field(default_factory=list)

class CodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.results = CheckResults()
        self.depth = 0

    def visit_FunctionDef(self, node):
        if len(node.body) > 50: self.results.long_functions.append(node.name)
        self.generic_visit(node)

    def visit_If(self, node):
        self.depth += 1
        if self.depth > 4: self.results.deep_nesting.append("If")
        self.generic_visit(node)
        self.depth -= 1

def check_code(source: str) -> CheckResults:
    tree = ast.parse(source)
    visitor = CodeVisitor()
    visitor.visit(tree)
    return visitor.results
