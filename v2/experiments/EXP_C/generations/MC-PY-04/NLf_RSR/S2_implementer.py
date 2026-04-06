import ast
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass


@dataclass
class UnusedImportIssue:
    """Issue for unused imports."""
    name: str
    line: int
    module: Optional[str] = None


@dataclass
class UnusedVariableIssue:
    """Issue for unused variables."""
    name: str
    line: int
    scope: str


@dataclass
class LongFunctionIssue:
    """Issue for functions longer than 50 lines."""
    function_name: str
    line: int
    length: int
    threshold: int = 50


@dataclass
class DeepNestingIssue:
    """Issue for nesting depth exceeding 4 levels."""
    function_name: str
    line: int
    max_depth: int
    threshold: int = 4


@dataclass
class CheckResult:
    """Aggregate result of code checking."""
    unused_imports: List[UnusedImportIssue]
    unused_variables: List[UnusedVariableIssue]
    long_functions: List[LongFunctionIssue]
    deep_nesting: List[DeepNestingIssue]
    total_issues: int
    source_lines: int


class ImportCollector(ast.NodeVisitor):
    """Collects all import names and their line numbers."""
    
    def __init__(self) -> None:
        super().__init__()
        self.imports: List[tuple[str, int, Optional[str]]] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append((alias.name, node.lineno, None))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module
        for alias in node.names:
            self.imports.append((alias.name, node.lineno, module))
        self.generic_visit(node)


class NameUsageCollector(ast.NodeVisitor):
    """Collects all name references (loads) in non-import contexts."""
    
    def __init__(self) -> None:
        super().__init__()
        self.usages: Set[str] = set()
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.usages.add(node.id)
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            try:
                attr_chain = []
                current = node
                while isinstance(current, ast.Attribute):
                    attr_chain.insert(0, current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    base = current.id
                    full_name = '.'.join([base] + attr_chain)
                    self.usages.add(full_name)
            except AttributeError:
                pass
        self.generic_visit(node)


class VariableTracker(ast.NodeVisitor):
    """Tracks variable assignments and usages per scope."""
    
    def __init__(self) -> None:
        super().__init__()
        self.scope_stack: List[Dict[str, tuple[bool, bool, int]]] = [{}]
        self.unused_vars: List[tuple[str, int, str]] = []
        self.current_function: str = "<module>"
    
    def _current_scope(self) -> Dict[str, tuple[bool, bool, int]]:
        return self.scope_stack[-1]
    
    def _find_in_scopes(self, name: str) -> Optional[Dict[str, tuple[bool, bool, int]]]:
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope
        return None
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope_stack.append({})
        old_function = self.current_function
        self.current_function = node.name
        
        for arg in node.args.args:
            self._current_scope()[arg.arg] = (True, False, node.lineno)
        
        self.generic_visit(node)
        
        for var_name, (assigned, used, line) in self._current_scope().items():
            if assigned and not used and not var_name.startswith('_'):
                self.unused_vars.append((var_name, line, self.current_function))
        
        self.scope_stack.pop()
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scope_stack.append({})
        old_function = self.current_function
        self.current_function = node.name
        
        for arg in node.args.args:
            self._current_scope()[arg.arg] = (True, False, node.lineno)
        
        self.generic_visit(node)
        
        for var_name, (assigned, used, line) in self._current_scope().items():
            if assigned and not used and not var_name.startswith('_'):
                self.unused_vars.append((var_name, line, self.current_function))
        
        self.scope_stack.pop()
        self.current_function = old_function
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._current_scope()[node.id] = (True, False, node.lineno)
        elif isinstance(node.ctx, ast.Load):
            scope = self._find_in_scopes(node.id)
            if scope:
                assigned, _, line = scope[node.id]
                scope[node.id] = (assigned, True, line)
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._current_scope()[target.id] = (True, False, node.lineno)
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For) -> None:
        if isinstance(node.target, ast.Name):
            self._current_scope()[node.target.id] = (True, True, node.lineno)
        self.generic_visit(node)
    
    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        if isinstance(node.target, ast.Name):
            self._current_scope()[node.target.id] = (True, True, node.lineno)
        self.generic_visit(node)


class FunctionAnalyzer(ast.NodeVisitor):
    """Analyzes function length and nesting depth."""
    
    def __init__(self) -> None:
        super().__init__()
        self.long_functions: List[tuple[str, int, int]] = []
        self.deep_nesting: List[tuple[str, int, int]] = []
        self.current_depth: int = 0
        self.max_depth_in_function: int = 0
        self.current_function: Optional[str] = None
        self.nesting_constructs = {
            ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
            ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler,
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
        }
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_function(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_function(node)
    
    def _analyze_function(self, node: ast.AST) -> None:
        old_function = self.current_function
        old_depth = self.current_depth
        old_max_depth = self.max_depth_in_function
        
        self.current_function = node.name if hasattr(node, 'name') else "anonymous"
        self.current_depth = 0
        self.max_depth_in_function = 0
        
        if hasattr(node, 'end_lineno') and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                self.long_functions.append((self.current_function, node.lineno, length))
        
        self.generic_visit(node)
        
        if self.max_depth_in_function > 4:
            self.deep_nesting.append((self.current_function, node.lineno, self.max_depth_in_function))
        
        self.current_function = old_function
        self.current_depth = old_depth
        self.max_depth_in_function = old_max_depth
    
    def generic_visit(self, node: ast.AST) -> None:
        if type(node) in self.nesting_constructs:
            self.current_depth += 1
            self.max_depth_in_function = max(self.max_depth_in_function, self.current_depth)
            super().generic_visit(node)
            self.current_depth -= 1
        else:
            super().generic_visit(node)


class CodeChecker:
    """Main code checker class."""
    
    def __init__(self) -> None:
        pass
    
    def check(self, source: str) -> CheckResult:
        """Perform all checks on source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return CheckResult([], [], [], [], 0, len(source.splitlines()))
        
        source_lines = len(source.splitlines())
        
        import_collector = ImportCollector()
        import_collector.visit(tree)
        imports = import_collector.imports
        
        usage_collector = NameUsageCollector()
        usage_collector.visit(tree)
        usages = usage_collector.usages
        
        unused_imports: List[UnusedImportIssue] = []
        for name, line, module in imports:
            if name not in usages and not name.startswith('_'):
                unused_imports.append(UnusedImportIssue(name=name, line=line, module=module))
        
        variable_tracker = VariableTracker()
        variable_tracker.visit(tree)
        unused_variables = [
            UnusedVariableIssue(name=name, line=line, scope=scope)
            for name, line, scope in variable_tracker.unused_vars
        ]
        
        function_analyzer = FunctionAnalyzer()
        function_analyzer.visit(tree)
        
        long_functions = [
            LongFunctionIssue(function_name=name, line=line, length=length)
            for name, line, length in function_analyzer.long_functions
        ]
        
        deep_nesting = [
            DeepNestingIssue(function_name=name, line=line, max_depth=depth)
            for name, line, depth in function_analyzer.deep_nesting
        ]
        
        total_issues = len(unused_imports) + len(unused_variables) + len(long_functions) + len(deep_nesting)
        
        return CheckResult(
            unused_imports=unused_imports,
            unused_variables=unused_variables,
            long_functions=long_functions,
            deep_nesting=deep_nesting,
            total_issues=total_issues,
            source_lines=source_lines
        )