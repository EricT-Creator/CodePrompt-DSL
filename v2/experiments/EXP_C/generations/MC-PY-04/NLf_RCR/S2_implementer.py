"""AST Code Checker - Analyzes Python code for various issues."""

import ast
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UnusedImportIssue:
    name: str
    line: int
    module: Optional[str]


@dataclass
class UnusedVariableIssue:
    name: str
    line: int
    scope: str


@dataclass
class LongFunctionIssue:
    function_name: str
    line: int
    length: int
    threshold: int


@dataclass
class DeepNestingIssue:
    function_name: str
    line: int
    max_depth: int
    threshold: int


@dataclass
class CheckResult:
    unused_imports: list[UnusedImportIssue] = field(default_factory=list)
    unused_variables: list[UnusedVariableIssue] = field(default_factory=list)
    long_functions: list[LongFunctionIssue] = field(default_factory=list)
    deep_nesting: list[DeepNestingIssue] = field(default_factory=list)
    total_issues: int = 0
    source_lines: int = 0


class ImportCollector(ast.NodeVisitor):
    """Collects all import names and their line numbers."""

    def __init__(self) -> None:
        self.imports: list[dict] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                'name': alias.asname if alias.asname else alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'module': None
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module
        for alias in node.names:
            self.imports.append({
                'name': alias.asname if alias.asname else alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'module': module
            })
        self.generic_visit(node)


class NameUsageCollector(ast.NodeVisitor):
    """Collects all name references (loads) in non-import contexts."""

    def __init__(self) -> None:
        self.used_names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            name_parts = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                name_parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                self.used_names.add(current.id)
        self.generic_visit(node)


class VariableTracker(ast.NodeVisitor):
    """Tracks variable assignments (stores) and usages per scope."""

    def __init__(self) -> None:
        self.scopes: list[dict] = [{}]
        self.unused_vars: list[UnusedVariableIssue] = []

    def _current_scope(self) -> dict:
        return self.scopes[-1]

    def _find_scope(self, name: str) -> Optional[dict]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope
        return None

    def _is_function_or_class_def(self, node: ast.AST) -> bool:
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))

    def _get_scope_name(self) -> str:
        for node in reversed(self.scopes):
            if hasattr(node, 'name'):
                return node.name
        return "<module>"

    def _push_scope(self, name: str = "<function>") -> None:
        self.scopes.append({'__name__': name})

    def _pop_scope(self) -> None:
        if len(self.scopes) > 1:
            scope = self.scopes.pop()
            scope_name = scope.get('__name__', '<function>')
            for var_name, info in scope.items():
                if var_name.startswith('__') and var_name.endswith('__'):
                    continue
                if isinstance(info, dict) and info.get('assigned') and not info.get('used'):
                    if not var_name.startswith('_'):
                        self.unused_vars.append(UnusedVariableIssue(
                            name=var_name,
                            line=info['line'],
                            scope=scope_name
                        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope(node.name)
        for arg in node.args.args:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        for arg in node.args.posonlyargs:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        for arg in node.args.kwonlyargs:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        if node.args.vararg:
            self._current_scope()[node.args.vararg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        if node.args.kwarg:
            self._current_scope()[node.args.kwarg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        self.generic_visit(node)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._push_scope(node.name)
        for arg in node.args.args:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        for arg in node.args.posonlyargs:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        for arg in node.args.kwonlyargs:
            self._current_scope()[arg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        if node.args.vararg:
            self._current_scope()[node.args.vararg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        if node.args.kwarg:
            self._current_scope()[node.args.kwarg.arg] = {'assigned': True, 'used': False, 'line': node.lineno}
        self.generic_visit(node)
        self._pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._push_scope(node.name)
        self.generic_visit(node)
        self._pop_scope()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if node.id != '_':
                self._current_scope()[node.id] = {'assigned': True, 'used': False, 'line': node.lineno}
        elif isinstance(node.ctx, ast.Load):
            scope = self._find_scope(node.id)
            if scope and node.id in scope and isinstance(scope[node.id], dict):
                scope[node.id]['used'] = True
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._handle_loop_vars(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._handle_loop_vars(node.target)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._handle_loop_vars(node.target)
        self.generic_visit(node)

    def _handle_loop_vars(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            if node.id != '_':
                self._current_scope()[node.id] = {'assigned': True, 'used': False, 'line': node.lineno}
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._handle_loop_vars(elt)

    def get_unused_variables(self) -> list[UnusedVariableIssue]:
        while len(self.scopes) > 1:
            self._pop_scope()
        module_scope = self.scopes[0]
        for var_name, info in module_scope.items():
            if var_name.startswith('__') and var_name.endswith('__'):
                continue
            if isinstance(info, dict) and info.get('assigned') and not info.get('used'):
                if not var_name.startswith('_'):
                    self.unused_vars.append(UnusedVariableIssue(
                        name=var_name,
                        line=info['line'],
                        scope='<module>'
                    ))
        return self.unused_vars


class FunctionAnalyzer(ast.NodeVisitor):
    """Visits function definitions to calculate line count and nesting depth."""

    NESTING_TYPES = (
        ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
        ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
    )

    def __init__(self) -> None:
        self.long_functions: list[LongFunctionIssue] = []
        self.deep_nesting: list[DeepNestingIssue] = []
        self.current_depth: int = 0
        self.max_depth: int = 0
        self.in_function: bool = False
        self.current_function_name: str = ""
        self.current_function_line: int = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_function(node)

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        was_in_function = self.in_function
        prev_depth = self.current_depth
        prev_max = self.max_depth
        prev_name = self.current_function_name
        prev_line = self.current_function_line

        self.in_function = True
        self.current_depth = 0
        self.max_depth = 0
        self.current_function_name = node.name
        self.current_function_line = node.lineno

        length = (node.end_lineno if node.end_lineno else node.lineno) - node.lineno + 1
        if length > 50:
            self.long_functions.append(LongFunctionIssue(
                function_name=node.name,
                line=node.lineno,
                length=length,
                threshold=50
            ))

        self.generic_visit(node)

        if self.max_depth > 4:
            self.deep_nesting.append(DeepNestingIssue(
                function_name=node.name,
                line=node.lineno,
                max_depth=self.max_depth,
                threshold=4
            ))

        self.in_function = was_in_function
        self.current_depth = prev_depth
        self.max_depth = prev_max
        self.current_function_name = prev_name
        self.current_function_line = prev_line

    def visit(self, node: ast.AST) -> None:
        if isinstance(node, self.NESTING_TYPES):
            self.current_depth += 1
            if self.in_function:
                self.max_depth = max(self.max_depth, self.current_depth)
        super().visit(node)
        if isinstance(node, self.NESTING_TYPES):
            self.current_depth -= 1


class CodeChecker:
    """Main orchestrator for code analysis."""

    def __init__(self) -> None:
        pass

    def check(self, source: str) -> CheckResult:
        """Parse source and run all checks."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return CheckResult(
                unused_imports=[],
                unused_variables=[],
                long_functions=[],
                deep_nesting=[],
                total_issues=0,
                source_lines=len(source.splitlines())
            )

        source_lines = len(source.splitlines())

        unused_imports = self.check_unused_imports(tree)
        unused_variables = self.check_unused_variables(tree)
        long_functions = self.check_long_functions(tree)
        deep_nesting = self.check_deep_nesting(tree)

        total_issues = (
            len(unused_imports) + len(unused_variables) +
            len(long_functions) + len(deep_nesting)
        )

        return CheckResult(
            unused_imports=unused_imports,
            unused_variables=unused_variables,
            long_functions=long_functions,
            deep_nesting=deep_nesting,
            total_issues=total_issues,
            source_lines=source_lines
        )

    def check_unused_imports(self, tree: ast.Module) -> list[UnusedImportIssue]:
        """Check for unused imports."""
        import_collector = ImportCollector()
        import_collector.visit(tree)

        name_collector = NameUsageCollector()
        name_collector.visit(tree)

        used_names = name_collector.used_names
        issues = []

        for imp in import_collector.imports:
            name = imp['name']
            if name not in used_names:
                if name != '*':
                    issues.append(UnusedImportIssue(
                        name=name,
                        line=imp['line'],
                        module=imp['module']
                    ))

        return issues

    def check_unused_variables(self, tree: ast.Module) -> list[UnusedVariableIssue]:
        """Check for unused variables."""
        tracker = VariableTracker()
        tracker.visit(tree)
        return tracker.get_unused_variables()

    def check_long_functions(self, tree: ast.Module) -> list[LongFunctionIssue]:
        """Check for functions longer than 50 lines."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.long_functions

    def check_deep_nesting(self, tree: ast.Module) -> list[DeepNestingIssue]:
        """Check for functions with nesting depth > 4."""
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        return analyzer.deep_nesting
