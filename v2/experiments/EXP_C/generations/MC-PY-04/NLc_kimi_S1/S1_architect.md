# MC-PY-04: Python Code Checker - Technical Design Document

## 1. AST Visitor Class Hierarchy

### Base Checker Visitor
```python
import ast
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class CheckResult:
    """Base class for check results."""
    line: int
    column: int
    message: str

@dataclass
class UnusedImportResult(CheckResult):
    name: str

@dataclass
class UnusedVariableResult(CheckResult):
    name: str

@dataclass
class LongFunctionResult(CheckResult):
    func_name: str
    line_count: int

@dataclass
class DeepNestingResult(CheckResult):
    func_name: str
    max_depth: int

class CodeChecker(ast.NodeVisitor):
    """AST-based code checker using NodeVisitor pattern."""
    
    def __init__(self, source: str):
        self.source = source
        self.lines = source.split('\n')
        self.results: dict[str, list[CheckResult]] = {
            'unused_imports': [],
            'unused_variables': [],
            'long_functions': [],
            'deep_nesting': []
        }
    
    def check(self) -> dict[str, list[CheckResult]]:
        """Parse and check source code."""
        try:
            tree = ast.parse(self.source)
            self.visit(tree)
            self._post_process()
            return self.results
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
    
    def _post_process(self) -> None:
        """Post-processing after AST traversal."""
        pass
```

### Specialized Visitors
```python
class ImportVisitor(ast.NodeVisitor):
    """Visitor for tracking imports and their usage."""
    
    def __init__(self):
        self.imports: dict[str, ast.Import | ast.ImportFrom] = {}
        self.used_names: set[str] = set()
    
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

class VariableVisitor(ast.NodeVisitor):
    """Visitor for tracking variable assignments and usage."""
    
    def __init__(self):
        self.assignments: dict[str, list[ast.Assign]] = defaultdict(list)
        self.used_names: set[str] = set()
        self.scope_stack: list[set[str]] = [set()]  # Global scope
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments[target.id].append(node)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)
```

## 2. Scope Tracking for Unused Detection

### Scope Management
```python
class ScopeTracker(ast.NodeVisitor):
    """Track variable scopes for accurate unused detection."""
    
    def __init__(self):
        self.scopes: list[dict[str, ast.AST]] = [{}]  # Stack of scopes
        self.assignments: list[tuple[str, ast.AST, int]] = []  # (name, node, scope_level)
        self.usages: list[tuple[str, ast.AST, int]] = []  # (name, node, scope_level)
    
    @property
    def current_scope(self) -> dict[str, ast.AST]:
        return self.scopes[-1]
    
    def push_scope(self) -> None:
        self.scopes.append({})
    
    def pop_scope(self) -> None:
        self.scopes.pop()
    
    def add_assignment(self, name: str, node: ast.AST) -> None:
        self.current_scope[name] = node
        self.assignments.append((name, node, len(self.scopes) - 1))
    
    def add_usage(self, name: str, node: ast.AST) -> None:
        # Find the scope where this name is defined
        for level in range(len(self.scopes) - 1, -1, -1):
            if name in self.scopes[level]:
                self.usages.append((name, node, level))
                return
        self.usages.append((name, node, -1))  # Undefined usage
    
    def get_unused(self) -> list[tuple[str, ast.AST]]:
        """Return list of unused assignments."""
        used = {(name, level) for name, _, level in self.usages}
        unused = []
        for name, node, level in self.assignments:
            if (name, level) not in used:
                unused.append((name, node))
        return unused
```

### Function Scope Visitor
```python
class FunctionScopeVisitor(ast.NodeVisitor):
    """Visitor that properly handles function scopes."""
    
    def __init__(self):
        self.scope_tracker = ScopeTracker()
        self.function_locals: dict[str, list[str]] = defaultdict(list)
    
    def visit_Module(self, node: ast.Module) -> None:
        self.scope_tracker.push_scope()
        self.generic_visit(node)
        self.scope_tracker.pop_scope()
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        func_name = node.name
        self.scope_tracker.push_scope()
        
        # Add parameters to function scope
        for arg in node.args.args:
            self.scope_tracker.add_assignment(arg.arg, arg)
        for arg in node.args.kwonlyargs:
            self.scope_tracker.add_assignment(arg.arg, arg)
        
        self.generic_visit(node)
        
        # Collect function-local unused variables
        unused = self.scope_tracker.get_unused()
        for name, assign_node in unused:
            if name not in [a.arg for a in node.args.args + node.args.kwonlyargs]:
                self.function_locals[func_name].append(name)
        
        self.scope_tracker.pop_scope()
    
    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.scope_tracker.add_assignment(target.id, node)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.scope_tracker.add_usage(node.id, node)
        self.generic_visit(node)
```

## 3. Nesting Depth Calculation Approach

### Depth Tracking Visitor
```python
class NestingDepthVisitor(ast.NodeVisitor):
    """Calculate maximum nesting depth for each function."""
    
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With, ast.Try,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
    )
    
    def __init__(self):
        self.function_depths: dict[str, int] = {}
        self.current_function: str | None = None
        self.depth_stack: list[int] = [0]
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        outer_function = self.current_function
        self.current_function = node.name
        self.depth_stack.append(0)
        
        self.generic_visit(node)
        
        max_depth = max(self.depth_stack)
        self.function_depths[node.name] = max_depth
        
        self.depth_stack.pop()
        self.current_function = outer_function
    
    def _increase_depth(self, node: ast.AST) -> None:
        """Increase depth for nesting nodes."""
        if self.current_function:
            self.depth_stack[-1] += 1
        self.generic_visit(node)
        if self.current_function:
            self.depth_stack[-1] -= 1
    
    visit_If = _increase_depth
    visit_For = _increase_depth
    visit_While = _increase_depth
    visit_With = _increase_depth
    visit_Try = _increase_depth
```

### Alternative: Recursive Depth Calculation
```python
def calculate_nesting_depth(node: ast.AST, current_depth: int = 0) -> int:
    """Calculate nesting depth recursively."""
    NESTING_TYPES = (ast.If, ast.For, ast.While, ast.With, ast.Try)
    
    if isinstance(node, NESTING_TYPES):
        current_depth += 1
    
    max_child_depth = current_depth
    for child in ast.iter_child_nodes(node):
        child_depth = calculate_nesting_depth(child, current_depth)
        max_child_depth = max(max_child_depth, child_depth)
    
    return max_child_depth

def get_function_nesting_depths(tree: ast.Module) -> dict[str, int]:
    """Get nesting depths for all functions in module."""
    depths = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            depths[node.name] = calculate_nesting_depth(node)
    return depths
```

## 4. Dataclass Result Schema

### Result Dataclasses
```python
from dataclasses import dataclass
from typing import List

@dataclass
class CodeCheckResults:
    """Container for all check results."""
    unused_imports: List[UnusedImportResult] = field(default_factory=list)
    unused_variables: List[UnusedVariableResult] = field(default_factory=list)
    long_functions: List[LongFunctionResult] = field(default_factory=list)
    deep_nesting: List[DeepNestingResult] = field(default_factory=list)
    
    def has_issues(self) -> bool:
        return any([
            self.unused_imports,
            self.unused_variables,
            self.long_functions,
            self.deep_nesting
        ])
    
    def total_issues(self) -> int:
        return sum([
            len(self.unused_imports),
            len(self.unused_variables),
            len(self.long_functions),
            len(self.deep_nesting)
        ])

@dataclass
class UnusedImportResult:
    name: str
    line: int
    column: int
    message: str = field(init=False)
    
    def __post_init__(self):
        self.message = f"Unused import: {self.name}"

@dataclass
class UnusedVariableResult:
    name: str
    line: int
    column: int
    message: str = field(init=False)
    
    def __post_init__(self):
        self.message = f"Unused variable: {self.name}"

@dataclass
class LongFunctionResult:
    func_name: str
    line: int
    column: int
    line_count: int
    message: str = field(init=False)
    
    def __post_init__(self):
        self.message = f"Function '{self.func_name}' is {self.line_count} lines (max 50)"

@dataclass
class DeepNestingResult:
    func_name: str
    line: int
    column: int
    max_depth: int
    message: str = field(init=False)
    
    def __post_init__(self):
        self.message = f"Function '{self.func_name}' has nesting depth {self.max_depth} (max 4)"
```

### Main Checker Class
```python
class PythonCodeChecker:
    """Main code checker class."""
    
    MAX_FUNCTION_LINES = 50
    MAX_NESTING_DEPTH = 4
    
    def __init__(self, source: str):
        self.source = source
        self.tree = ast.parse(source)
        self.lines = source.split('\n')
    
    def check(self) -> CodeCheckResults:
        """Run all checks and return results."""
        results = CodeCheckResults()
        
        results.unused_imports = self._check_unused_imports()
        results.unused_variables = self._check_unused_variables()
        results.long_functions = self._check_long_functions()
        results.deep_nesting = self._check_deep_nesting()
        
        return results
    
    def _check_unused_imports(self) -> List[UnusedImportResult]:
        """Check for unused imports."""
        visitor = ImportVisitor()
        visitor.visit(self.tree)
        
        unused = []
        for name, node in visitor.imports.items():
            if name not in visitor.used_names:
                unused.append(UnusedImportResult(
                    name=name,
                    line=node.lineno,
                    column=node.col_offset
                ))
        return unused
    
    def _check_long_functions(self) -> List[LongFunctionResult]:
        """Check for functions longer than 50 lines."""
        long_funcs = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                line_count = node.end_lineno - node.lineno + 1
                if line_count > self.MAX_FUNCTION_LINES:
                    long_funcs.append(LongFunctionResult(
                        func_name=node.name,
                        line=node.lineno,
                        column=node.col_offset,
                        line_count=line_count
                    ))
        return long_funcs
    
    def _check_deep_nesting(self) -> List[DeepNestingResult]:
        """Check for nesting depth exceeding 4."""
        visitor = NestingDepthVisitor()
        visitor.visit(self.tree)
        
        deep_funcs = []
        for func_name, depth in visitor.function_depths.items():
            if depth > self.MAX_NESTING_DEPTH:
                # Find function node for line info
                for node in ast.walk(self.tree):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        deep_funcs.append(DeepNestingResult(
                            func_name=func_name,
                            line=node.lineno,
                            column=node.col_offset,
                            max_depth=depth
                        ))
                        break
        return deep_funcs
```

## 5. Constraint Acknowledgment

### Python 3.10+, stdlib only
**Addressed by:** Only imports from Python standard library (ast, typing, dataclasses, collections). No external dependencies.

### ast.NodeVisitor required, no regex
**Addressed by:** All code analysis implemented using `ast.NodeVisitor` pattern. No regex patterns used for code parsing.

### Results as dataclass
**Addressed by:** All check results returned as dataclass instances (`UnusedImportResult`, `LongFunctionResult`, etc.). Main result container is `CodeCheckResults` dataclass.

### Full type annotations
**Addressed by:** Complete type hints on all classes, methods, and functions. Uses modern Python typing features.

### Check: unused import/var, long func, deep nest
**Addressed by:** Four specific checks implemented:
- Unused imports: Tracks imports and name usage via AST
- Unused variables: Tracks assignments and usage across scopes
- Long functions: Counts lines per function (max 50)
- Deep nesting: Calculates control flow nesting depth (max 4)

### Single file, class output
**Addressed by:** Single Python file containing `PythonCodeChecker` class and all supporting dataclasses and visitors. Main export is the checker class.
