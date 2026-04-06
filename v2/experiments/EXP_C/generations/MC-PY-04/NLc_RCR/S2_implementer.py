import ast
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class UnusedImport:
    name: str
    line: int

@dataclass
class UnusedVariable:
    name: str
    line: int
    scope: str

@dataclass
class LongFunction:
    name: str
    line: int
    length: int

@dataclass
class NestingIssue:
    line: int
    depth: int

@dataclass
class CheckResult:
    unused_imports: list[UnusedImport] = field(default_factory=list)
    unused_variables: list[UnusedVariable] = field(default_factory=list)
    long_functions: list[LongFunction] = field(default_factory=list)
    nesting_issues: list[NestingIssue] = field(default_factory=list)
    
    @property
    def total_issues(self) -> int:
        return (len(self.unused_imports) + len(self.unused_variables) + 
                len(self.long_functions) + len(self.nesting_issues))

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: dict[str, int] = {}
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            if alias.name == '*':
                continue
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

class NameUsageVisitor(ast.NodeVisitor):
    def __init__(self):
        self.used_names: set[str] = set()
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

class VariableVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments: list[tuple[str, int, str]] = []
        self.usages: list[tuple[str, str]] = []
        self.current_scope: str = "<module>"
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_scope = self.current_scope
        self.current_scope = node.name
        for arg in node.args.args:
            self.usages.append((arg.arg, self.current_scope))
        self.generic_visit(node)
        self.current_scope = old_scope
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.assignments.append((node.id, node.lineno, self.current_scope))
        elif isinstance(node.ctx, ast.Load):
            self.usages.append((node.id, self.current_scope))
        self.generic_visit(node)

class FunctionLengthVisitor(ast.NodeVisitor):
    def __init__(self):
        self.long_functions: list[LongFunction] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                self.long_functions.append(LongFunction(
                    name=node.name,
                    line=node.lineno,
                    length=length
                ))
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                self.long_functions.append(LongFunction(
                    name=node.name,
                    line=node.lineno,
                    length=length
                ))
        self.generic_visit(node)

class NestingDepthVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_depth: int = 0
        self.violations: list[NestingIssue] = []
    
    def _visit_nesting_node(self, node):
        self.current_depth += 1
        if self.current_depth > 4:
            self.violations.append(NestingIssue(
                line=node.lineno,
                depth=self.current_depth
            ))
        self.generic_visit(node)
        self.current_depth -= 1
    
    visit_If = _visit_nesting_node
    visit_For = _visit_nesting_node
    visit_While = _visit_nesting_node
    visit_With = _visit_nesting_node
    visit_Try = _visit_nesting_node

class CodeChecker:
    def check(self, source: str) -> CheckResult:
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result = CheckResult()
            return result
        
        import_visitor = ImportVisitor()
        import_visitor.visit(tree)
        
        usage_visitor = NameUsageVisitor()
        usage_visitor.visit(tree)
        
        variable_visitor = VariableVisitor()
        variable_visitor.visit(tree)
        
        func_visitor = FunctionLengthVisitor()
        func_visitor.visit(tree)
        
        nesting_visitor = NestingDepthVisitor()
        nesting_visitor.visit(tree)
        
        unused_imports = [
            UnusedImport(name=name, line=line)
            for name, line in import_visitor.imports.items()
            if name not in usage_visitor.used_names
        ]
        
        unused_variables: list[UnusedVariable] = []
        for var_name, line, scope in variable_visitor.assignments:
            if var_name.startswith('_'):
                continue
            is_used = any(
                used_name == var_name and (used_scope == scope or scope == "<module>")
                for used_name, used_scope in variable_visitor.usages
            )
            if not is_used:
                unused_variables.append(UnusedVariable(
                    name=var_name,
                    line=line,
                    scope=scope
                ))
        
        return CheckResult(
            unused_imports=unused_imports,
            unused_variables=unused_variables,
            long_functions=func_visitor.long_functions,
            nesting_issues=nesting_visitor.violations
        )
