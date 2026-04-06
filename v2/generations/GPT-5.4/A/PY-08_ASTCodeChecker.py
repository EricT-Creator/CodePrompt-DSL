import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class UnusedImportIssue:
    name: str
    line: int


@dataclass
class UnusedVariableIssue:
    name: str
    line: int


@dataclass
class LongFunctionIssue:
    name: str
    line: int
    length: int


@dataclass
class DeepNestingIssue:
    line: int
    depth: int
    node_type: str


@dataclass
class CheckResults:
    unused_imports: List[UnusedImportIssue] = field(default_factory=list)
    unused_variables: List[UnusedVariableIssue] = field(default_factory=list)
    long_functions: List[LongFunctionIssue] = field(default_factory=list)
    deep_nesting: List[DeepNestingIssue] = field(default_factory=list)


class Scope:
    def __init__(self) -> None:
        self.imports: Dict[str, int] = {}
        self.assigned: Dict[str, int] = {}
        self.read: Set[str] = set()


class UsageAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: List[Scope] = [Scope()]
        self.results = CheckResults()

    @property
    def current_scope(self) -> Scope:
        return self.scopes[-1]

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.current_scope.imports[name] = node.lineno

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.current_scope.imports[name] = node.lineno

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._mark_read(node.id)
        elif isinstance(node.ctx, ast.Store):
            if node.id != "_":
                self.current_scope.assigned.setdefault(node.id, node.lineno)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function_length(node)
        self._visit_scoped_body(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function_length(node)
        self._visit_scoped_body(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(Scope())
        for statement in node.body:
            self.visit(statement)
        scope = self.scopes.pop()
        self._collect_scope_issues(scope)

    def _visit_scoped_body(self, node: ast.AST) -> None:
        self.scopes.append(Scope())
        for statement in getattr(node, "body", []):
            self.visit(statement)
        scope = self.scopes.pop()
        self._collect_scope_issues(scope)

    def _record_function_length(self, node: ast.AST) -> None:
        end_line = getattr(node, "end_lineno", getattr(node, "lineno", 0))
        start_line = getattr(node, "lineno", 0)
        length = max(0, end_line - start_line + 1)
        if length > 50:
            self.results.long_functions.append(
                LongFunctionIssue(
                    name=getattr(node, "name", "<lambda>"),
                    line=start_line,
                    length=length,
                )
            )

    def _mark_read(self, name: str) -> None:
        for scope in reversed(self.scopes):
            if name in scope.imports or name in scope.assigned:
                scope.read.add(name)
                return
        self.current_scope.read.add(name)

    def _collect_scope_issues(self, scope: Scope) -> None:
        for name, line in scope.imports.items():
            if name not in scope.read:
                self.results.unused_imports.append(UnusedImportIssue(name=name, line=line))
        for name, line in scope.assigned.items():
            if name not in scope.read and name not in scope.imports:
                self.results.unused_variables.append(UnusedVariableIssue(name=name, line=line))

    def finalize(self) -> None:
        self._collect_scope_issues(self.scopes[0])


class NestingAnalyzer(ast.NodeVisitor):
    TARGET_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)

    def __init__(self) -> None:
        self.results: List[DeepNestingIssue] = []

    def visit(self, node: ast.AST, depth: int = 0):
        if isinstance(node, self.TARGET_NODES):
            depth += 1
            if depth > 4:
                self.results.append(
                    DeepNestingIssue(
                        line=getattr(node, "lineno", 0),
                        depth=depth,
                        node_type=type(node).__name__,
                    )
                )

        for child in ast.iter_child_nodes(node):
            self.visit(child, depth)


def check_code(source: str) -> CheckResults:
    tree = ast.parse(source)

    usage = UsageAnalyzer()
    usage.visit(tree)
    usage.finalize()

    nesting = NestingAnalyzer()
    nesting.visit(tree)
    usage.results.deep_nesting = nesting.results
    return usage.results


if __name__ == "__main__":
    sample = """
import os
import sys


def example():
    x = 1
    y = 2
    return x
"""
    print(check_code(sample))
