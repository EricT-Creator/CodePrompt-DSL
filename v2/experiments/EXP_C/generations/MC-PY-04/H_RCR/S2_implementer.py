from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Set


@dataclass
class CheckResult:
    check_type: Literal["unused_import", "unused_variable", "long_function", "deep_nesting"]
    message: str
    line: int
    column: int
    severity: Literal["warning", "error"]
    context: str


@dataclass
class CheckReport:
    issues: List[CheckResult]
    total: int
    by_type: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.by_type = {}
        for issue in self.issues:
            self.by_type[issue.check_type] = self.by_type.get(issue.check_type, 0) + 1


@dataclass
class ScopeInfo:
    name: str
    defined: Dict[str, int] = field(default_factory=dict)
    used: Set[str] = field(default_factory=set)


class ImportChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imported: Dict[str, int] = {}
        self.used_names: Set[str] = set()
        self.results: List[CheckResult] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if '.' in alias.name and not alias.asname:
                name = alias.name.split('.')[0]
            self.imported[name] = node.lineno if node.lineno else 0

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported[name] = node.lineno if node.lineno else 0

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)

    def run(self, tree: ast.AST) -> List[CheckResult]:
        self.imported = {}
        self.used_names = set()
        self.results = []

        self.visit(tree)

        for name, line in self.imported.items():
            if name not in self.used_names:
                self.results.append(CheckResult(
                    check_type="unused_import",
                    message=f"Import '{name}' is imported but never used",
                    line=line,
                    column=0,
                    severity="warning",
                    context=name
                ))

        return self.results


class VariableChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scopes: List[ScopeInfo] = [ScopeInfo(name="module")]
        self.results: List[CheckResult] = []

    def _current_scope(self) -> ScopeInfo:
        return self.scopes[-1]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes.append(ScopeInfo(name=node.name))
        self.generic_visit(node)

        scope = self.scopes.pop()
        for var_name, line in scope.defined.items():
            if var_name.startswith('_'):
                continue
            if var_name not in scope.used:
                self.results.append(CheckResult(
                    check_type="unused_variable",
                    message=f"Variable '{var_name}' is defined but never used",
                    line=line,
                    column=0,
                    severity="warning",
                    context=scope.name
                ))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(ScopeInfo(name=node.name))
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                scope = self._current_scope()
                if target.id not in scope.defined:
                    scope.defined[target.id] = node.lineno if node.lineno else 0
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            scope = self._current_scope()
            if node.target.id not in scope.defined:
                scope.defined[node.target.id] = node.lineno if node.lineno else 0
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            for scope in reversed(self.scopes):
                scope.used.add(node.id)

    def run(self, tree: ast.AST) -> List[CheckResult]:
        self.scopes = [ScopeInfo(name="module")]
        self.results = []
        self.visit(tree)
        return self.results


class FunctionLengthChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.results: List[CheckResult] = []
        self.MAX_LINES = 50

    def _get_function_lines(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if node.lineno and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        lines = self._get_function_lines(node)
        if lines > self.MAX_LINES:
            self.results.append(CheckResult(
                check_type="long_function",
                message=f"Function '{node.name}' has {lines} lines (max allowed: {self.MAX_LINES})",
                line=node.lineno if node.lineno else 0,
                column=node.col_offset if node.col_offset else 0,
                severity="warning",
                context=node.name
            ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def run(self, tree: ast.AST) -> List[CheckResult]:
        self.results = []
        self.visit(tree)
        return self.results


class NestingDepthChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.results: List[CheckResult] = []
        self.MAX_DEPTH = 4
        self.current_depth = 0
        self.max_depth = 0
        self.function_name = ""
        self.function_node: Optional[ast.AST] = None

    NESTING_NODES = {
        ast.If, ast.For, ast.While, ast.AsyncFor,
        ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler
    }

    def _check_nesting(self, node: ast.AST) -> None:
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_depth = self.current_depth
        old_max = self.max_depth
        old_name = self.function_name
        old_func_node = self.function_node

        self.current_depth = 0
        self.max_depth = 0
        self.function_name = node.name
        self.function_node = node

        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.arguments, ast.decorator_list)):
                self.visit(child)

        if self.max_depth > self.MAX_DEPTH:
            self.results.append(CheckResult(
                check_type="deep_nesting",
                message=f"Function '{node.name}' has nesting depth {self.max_depth} (max allowed: {self.MAX_DEPTH})",
                line=node.lineno if node.lineno else 0,
                column=node.col_offset if node.col_offset else 0,
                severity="warning",
                context=node.name
            ))

        self.current_depth = old_depth
        self.max_depth = old_max
        self.function_name = old_name
        self.function_node = old_func_node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_nesting(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_nesting(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._check_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_nesting(node)

    def visit_With(self, node: ast.With) -> None:
        self._check_nesting(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._check_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._check_nesting(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._check_nesting(node)

    def run(self, tree: ast.AST) -> List[CheckResult]:
        self.results = []
        self.current_depth = 0
        self.max_depth = 0
        self.function_name = ""
        self.function_node = None
        self.visit(tree)
        return self.results


class CodeChecker:
    def check(self, source: str) -> CheckReport:
        tree = ast.parse(source)
        results: List[CheckResult] = []

        results.extend(ImportChecker().run(tree))
        results.extend(VariableChecker().run(tree))
        results.extend(FunctionLengthChecker().run(tree))
        results.extend(NestingDepthChecker().run(tree))

        return CheckReport(issues=results, total=len(results))
