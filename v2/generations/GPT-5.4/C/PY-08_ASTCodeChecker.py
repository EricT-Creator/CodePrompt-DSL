import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NameIssue:
    name: str
    line: int


@dataclass
class FunctionIssue:
    name: str
    line: int
    length: int


@dataclass
class NestingIssue:
    line: int
    depth: int
    node_type: str


@dataclass
class CheckResults:
    unused_imports: list[NameIssue] = field(default_factory=list)
    unused_vars: list[NameIssue] = field(default_factory=list)
    long_functions: list[FunctionIssue] = field(default_factory=list)
    deep_nesting: list[NestingIssue] = field(default_factory=list)


class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: dict[str, int] = {}
        self.used_names: set[str] = set()
        self.scope_stack: list[dict[str, int]] = [{}]
        self.long_functions: list[FunctionIssue] = []
        self.deep_nesting: list[NestingIssue] = []
        self.current_depth = 0

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            imported_name = alias.asname or alias.name.split('.')[0]
            self.imports[imported_name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        for alias in node.names:
            imported_name = alias.asname or alias.name
            self.imports[imported_name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.scope_stack[-1].setdefault(node.id, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._handle_function(node)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_line = getattr(node, 'end_lineno', node.lineno)
        length = end_line - node.lineno + 1
        if length > 50:
            self.long_functions.append(FunctionIssue(name=node.name, line=node.lineno, length=length))

        self.scope_stack.append({})
        for argument in node.args.args + node.args.kwonlyargs:
            self.scope_stack[-1][argument.arg] = argument.lineno
        if node.args.vararg:
            self.scope_stack[-1][node.args.vararg.arg] = node.args.vararg.lineno
        if node.args.kwarg:
            self.scope_stack[-1][node.args.kwarg.arg] = node.args.kwarg.lineno

        self.generic_visit(node)
        self.scope_stack.append(self.scope_stack.pop())

    def visit_If(self, node: ast.If) -> Any:
        self._visit_nested(node)

    def visit_For(self, node: ast.For) -> Any:
        self._visit_nested(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        self._visit_nested(node)

    def visit_While(self, node: ast.While) -> Any:
        self._visit_nested(node)

    def visit_With(self, node: ast.With) -> Any:
        self._visit_nested(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
        self._visit_nested(node)

    def visit_Try(self, node: ast.Try) -> Any:
        self._visit_nested(node)

    def _visit_nested(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > 4:
            self.deep_nesting.append(
                NestingIssue(line=getattr(node, 'lineno', 0), depth=self.current_depth, node_type=type(node).__name__)
            )
        self.generic_visit(node)
        self.current_depth -= 1


def collect_unused_variables(tree: ast.AST, analyzer: CodeAnalyzer) -> list[NameIssue]:
    assigned: dict[str, int] = {}

    class AssignedCollector(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> Any:
            if isinstance(node.ctx, ast.Store):
                assigned.setdefault(node.id, node.lineno)
            self.generic_visit(node)

    AssignedCollector().visit(tree)
    issues: list[NameIssue] = []
    for name, line in assigned.items():
        if name not in analyzer.used_names and name not in analyzer.imports:
            issues.append(NameIssue(name=name, line=line))
    return sorted(issues, key=lambda item: (item.line, item.name))


def check_code(source: str) -> CheckResults:
    tree = ast.parse(source)
    analyzer = CodeAnalyzer()
    analyzer.visit(tree)

    unused_imports = [
        NameIssue(name=name, line=line)
        for name, line in sorted(analyzer.imports.items(), key=lambda item: (item[1], item[0]))
        if name not in analyzer.used_names
    ]
    unused_vars = collect_unused_variables(tree, analyzer)

    return CheckResults(
        unused_imports=unused_imports,
        unused_vars=unused_vars,
        long_functions=sorted(analyzer.long_functions, key=lambda item: (item.line, item.name)),
        deep_nesting=sorted(analyzer.deep_nesting, key=lambda item: (item.line, item.depth)),
    )


if __name__ == "__main__":
    SAMPLE = '''
import os
import math

value = 3

def demo(items):
    total = 0
    for item in items:
        if item > 0:
            for inner in range(item):
                while inner > 0:
                    if inner % 2 == 0:
                        total += inner
                    inner -= 1
    return total
'''
    print(check_code(SAMPLE))
