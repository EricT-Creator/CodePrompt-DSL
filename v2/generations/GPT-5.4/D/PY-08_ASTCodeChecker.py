from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Finding:
    name: str
    line: int
    detail: str


@dataclass
class CheckResults:
    unused_imports: list[Finding] = field(default_factory=list)
    unused_variables: list[Finding] = field(default_factory=list)
    long_functions: list[Finding] = field(default_factory=list)
    deep_nesting: list[Finding] = field(default_factory=list)


@dataclass
class Scope:
    kind: str
    name: str
    assigned: dict[str, int] = field(default_factory=dict)
    imported: dict[str, int] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    definitions: set[str] = field(default_factory=set)


class CodeChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.results = CheckResults()
        self.scope_stack: list[Scope] = [Scope(kind="module", name="<module>")]
        self.nesting_depth = 0

    @property
    def current_scope(self) -> Scope:
        return self.scope_stack[-1]

    def enter_scope(self, kind: str, name: str) -> None:
        self.scope_stack.append(Scope(kind=kind, name=name))

    def leave_scope(self) -> None:
        scope = self.scope_stack.pop()

        for name, line in scope.imported.items():
            if name not in scope.used and name != "*":
                self.results.unused_imports.append(
                    Finding(name=name, line=line, detail=f"Unused import in {scope.name}")
                )

        for name, line in scope.assigned.items():
            if name.startswith("_") or name in scope.definitions:
                continue
            if name not in scope.used:
                self.results.unused_variables.append(
                    Finding(name=name, line=line, detail=f"Unused variable in {scope.name}")
                )

    def mark_used(self, name: str) -> None:
        for scope in reversed(self.scope_stack):
            if name in scope.assigned or name in scope.imported:
                scope.used.add(name)
                return

    def register_assigned(self, names: Iterable[str], line: int) -> None:
        for name in names:
            if name:
                self.current_scope.assigned.setdefault(name, line)

    def register_definition(self, name: str, line: int) -> None:
        self.current_scope.assigned.setdefault(name, line)
        self.current_scope.definitions.add(name)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.current_scope.imported.setdefault(name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.current_scope.imported.setdefault(name, node.lineno)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.mark_used(node.id)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.register_assigned(self.extract_target_names(target), node.lineno)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
        self.register_assigned(self.extract_target_names(node.target), node.lineno)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        for name in self.extract_target_names(node.target):
            self.mark_used(name)
        self.visit(node.value)
        self.register_assigned(self.extract_target_names(node.target), node.lineno)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self.register_assigned(self.extract_target_names(node.target), node.lineno)
        self.visit_control_block(node, [node.body, node.orelse], "for")

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)
        self.register_assigned(self.extract_target_names(node.target), node.lineno)
        self.visit_control_block(node, [node.body, node.orelse], "async for")

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self.visit_control_block(node, [node.body, node.orelse], "while")

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        self.visit_control_block(node, [node.body, node.orelse], "if")

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.register_assigned(self.extract_target_names(item.optional_vars), node.lineno)
        self.visit_control_block(node, [node.body], "with")

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.register_assigned(self.extract_target_names(item.optional_vars), node.lineno)
        self.visit_control_block(node, [node.body], "async with")

    def visit_Try(self, node: ast.Try) -> None:
        self.nesting_depth += 1
        if self.nesting_depth > 4:
            self.results.deep_nesting.append(
                Finding(name="try", line=node.lineno, detail=f"Nesting depth {self.nesting_depth} exceeds 4")
            )
        for child in node.body:
            self.visit(child)
        for handler in node.handlers:
            self.visit(handler)
        for child in node.orelse:
            self.visit(child)
        for child in node.finalbody:
            self.visit(child)
        self.nesting_depth -= 1

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is not None:
            self.visit(node.type)
        if node.name:
            self.register_assigned([node.name], node.lineno)
        for child in node.body:
            self.visit(child)

    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        self.nesting_depth += 1
        if self.nesting_depth > 4:
            self.results.deep_nesting.append(
                Finding(name="match", line=node.lineno, detail=f"Nesting depth {self.nesting_depth} exceeds 4")
            )
        for case in node.cases:
            if case.guard is not None:
                self.visit(case.guard)
            for child in case.body:
                self.visit(child)
        self.nesting_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.register_definition(node.name, node.lineno)
        self.record_function_length(node)
        for decorator in node.decorator_list:
            self.visit(decorator)
        if node.returns is not None:
            self.visit(node.returns)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)

        self.enter_scope("function", node.name)
        argument_names = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
        if node.args.vararg:
            argument_names.append(node.args.vararg.arg)
        if node.args.kwarg:
            argument_names.append(node.args.kwarg.arg)
        self.register_assigned(argument_names, node.lineno)
        for child in node.body:
            self.visit(child)
        self.leave_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.register_definition(node.name, node.lineno)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)

        self.enter_scope("class", node.name)
        for child in node.body:
            self.visit(child)
        self.leave_scope()

    def record_function_length(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        length = end_lineno - node.lineno + 1
        if length > 50:
            self.results.long_functions.append(
                Finding(name=node.name, line=node.lineno, detail=f"Function length is {length} lines")
            )

    def visit_control_block(self, node: ast.AST, blocks: list[list[ast.stmt]], name: str) -> None:
        self.nesting_depth += 1
        if self.nesting_depth > 4:
            self.results.deep_nesting.append(
                Finding(name=name, line=getattr(node, "lineno", 0), detail=f"Nesting depth {self.nesting_depth} exceeds 4")
            )
        for block in blocks:
            for child in block:
                self.visit(child)
        self.nesting_depth -= 1

    def extract_target_names(self, target: ast.AST) -> list[str]:
        if isinstance(target, ast.Name):
            return [target.id]
        if isinstance(target, (ast.Tuple, ast.List)):
            names: list[str] = []
            for element in target.elts:
                names.extend(self.extract_target_names(element))
            return names
        if isinstance(target, ast.Starred):
            return self.extract_target_names(target.value)
        return []


def check_code(source: str) -> CheckResults:
    tree = ast.parse(source)
    checker = CodeChecker()
    checker.visit(tree)
    while checker.scope_stack:
        checker.leave_scope()
    return checker.results


if __name__ == "__main__":
    sample = """
import os
import math

value = 1
unused = 2

def demo():
    total = value
    for number in range(2):
        if number:
            while total < 10:
                for inner in range(2):
                    if inner:
                        total += inner
    return total
"""
    results = check_code(sample)
    print(results)
