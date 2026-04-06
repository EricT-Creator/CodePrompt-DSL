import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Issue:
    name: str
    line: int
    message: str


@dataclass
class CheckResults:
    unused_imports: List[Issue] = field(default_factory=list)
    unused_variables: List[Issue] = field(default_factory=list)
    long_functions: List[Issue] = field(default_factory=list)
    deep_nesting: List[Issue] = field(default_factory=list)


@dataclass
class Scope:
    assigned: Dict[str, int] = field(default_factory=dict)
    imported: Dict[str, int] = field(default_factory=dict)
    used: Set[str] = field(default_factory=set)


class CodeChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.results = CheckResults()
        self.scopes: List[Scope] = [Scope()]
        self.nesting_depth = 0

    @property
    def current_scope(self) -> Scope:
        return self.scopes[-1]

    def push_scope(self) -> None:
        self.scopes.append(Scope())

    def pop_scope(self) -> None:
        scope = self.scopes.pop()
        for name, line in sorted(scope.imported.items(), key=lambda item: item[1]):
            if name not in scope.used and not name.startswith("_"):
                self.results.unused_imports.append(
                    Issue(name=name, line=line, message=f"Imported name '{name}' is never used")
                )
        for name, line in sorted(scope.assigned.items(), key=lambda item: item[1]):
            if name not in scope.used and not name.startswith("_") and name not in {"self", "cls"}:
                self.results.unused_variables.append(
                    Issue(name=name, line=line, message=f"Variable '{name}' is assigned but never used")
                )

    def mark_used(self, name: str) -> None:
        for scope in reversed(self.scopes):
            if name in scope.assigned or name in scope.imported:
                scope.used.add(name)
                return

    def add_assigned_names(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.current_scope.assigned.setdefault(target.id, target.lineno)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self.add_assigned_names(element)

    def track_nesting(self, node: ast.AST) -> None:
        self.nesting_depth += 1
        if self.nesting_depth > 4:
            self.results.deep_nesting.append(
                Issue(
                    name=type(node).__name__,
                    line=getattr(node, "lineno", 0),
                    message=f"Nesting depth {self.nesting_depth} exceeds 4 levels",
                )
            )
        self.generic_visit(node)
        self.nesting_depth -= 1

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_name = alias.asname or alias.name.split(".")[0]
            self.current_scope.imported.setdefault(imported_name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            imported_name = alias.asname or alias.name
            self.current_scope.imported.setdefault(imported_name, node.lineno)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self.add_assigned_names(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.add_assigned_names(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.add_assigned_names(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.add_assigned_names(node.target)
        self.track_nesting(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.add_assigned_names(node.target)
        self.track_nesting(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self.add_assigned_names(item.optional_vars)
        self.track_nesting(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self.add_assigned_names(item.optional_vars)
        self.track_nesting(node)

    def visit_If(self, node: ast.If) -> None:
        self.track_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self.track_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.track_nesting(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.track_nesting(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.current_scope.assigned.setdefault(node.name, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.mark_used(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.current_scope.assigned.setdefault(node.name, node.lineno)
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.current_scope.assigned.setdefault(node.name, node.lineno)
        self._visit_function(node)

    def _visit_function(self, node: ast.AST) -> None:
        lineno = getattr(node, "lineno", 0)
        end_lineno = getattr(node, "end_lineno", lineno)
        length = end_lineno - lineno + 1
        function_name = getattr(node, "name", "<lambda>")
        if length > 50:
            self.results.long_functions.append(
                Issue(
                    name=function_name,
                    line=lineno,
                    message=f"Function '{function_name}' has {length} lines (> 50)",
                )
            )

        self.push_scope()
        arguments = getattr(node, "args")
        all_args = list(arguments.posonlyargs) + list(arguments.args) + list(arguments.kwonlyargs)
        if arguments.vararg is not None:
            all_args.append(arguments.vararg)
        if arguments.kwarg is not None:
            all_args.append(arguments.kwarg)
        for argument in all_args:
            self.current_scope.assigned.setdefault(argument.arg, argument.lineno)
        self.generic_visit(node)
        self.pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.current_scope.assigned.setdefault(node.name, node.lineno)
        self.push_scope()
        self.generic_visit(node)
        self.pop_scope()

    def finalize(self) -> CheckResults:
        while len(self.scopes) > 1:
            self.pop_scope()
        self.pop_scope()
        self.scopes.append(Scope())
        return self.results


def check_code(source: str) -> CheckResults:
    tree = ast.parse(source)
    checker = CodeChecker()
    checker.visit(tree)
    return checker.finalize()


if __name__ == "__main__":
    SAMPLE_CODE = """
import os
import math

unused_value = 10


def demo(items):
    total = 0
    for item in items:
        if item > 0:
            if item % 2 == 0:
                if item > 10:
                    if item > 20:
                        if item > 30:
                            total += item
    return total
"""

    result = check_code(SAMPLE_CODE)
    print(result)
