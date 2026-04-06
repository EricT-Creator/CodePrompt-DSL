# MC-PY-04: AST Code Checker — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. AST Visitor Class Hierarchy

### 1.1 Base Visitor

```python
import ast
from typing import Any
from dataclasses import dataclass, field

class BaseVisitor(ast.NodeVisitor):
    """Base class for AST visitors"""
    
    def __init__(self):
        self.issues: list[Issue] = []
    
    def add_issue(self, issue_type: str, message: str, node: ast.AST):
        """Record an issue found during analysis"""
        self.issues.append(Issue(
            type=issue_type,
            message=message,
            line=node.lineno,
            col=node.col_offset
        ))
```

### 1.2 Specialized Visitors

```python
class ImportVisitor(BaseVisitor):
    """Detect unused imports"""
    def __init__(self):
        super().__init__()
        self.imports: dict[str, ast.Import] = {}
        self.used_names: set[str] = set()
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = node
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

class VariableVisitor(BaseVisitor):
    """Detect unused variables"""
    def __init__(self):
        super().__init__()
        self.scopes: list[set[str]] = [set()]  # Stack of scopes
        self.defined: dict[str, ast.AST] = {}
        self.used: set[str] = set()
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scopes.append(set())
        self.generic_visit(node)
        self._check_unused_in_scope()
        self.scopes.pop()
    
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.scopes[-1].add(node.id)
            self.defined[node.id] = node
        elif isinstance(node.ctx, ast.Load):
            self.used.add(node.id)
```

### 1.3 Length Visitor

```python
class FunctionLengthVisitor(BaseVisitor):
    """Detect functions longer than 50 lines"""
    MAX_LINES = 50
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        length = node.end_lineno - node.lineno + 1
        if length > self.MAX_LINES:
            self.add_issue(
                "long_function",
                f"Function '{node.name}' is {length} lines (max {self.MAX_LINES})",
                node
            )
        self.generic_visit(node)
```

### 1.4 Nesting Visitor

```python
class NestingVisitor(BaseVisitor):
    """Detect nesting depth > 4"""
    MAX_DEPTH = 4
    
    def __init__(self):
        super().__init__()
        self.current_depth = 0
        self.nesting_nodes = (
            ast.If, ast.For, ast.While, ast.With,
            ast.FunctionDef, ast.ClassDef, ast.Try
        )
    
    def visit(self, node: ast.AST):
        is_nesting = isinstance(node, self.nesting_nodes)
        
        if is_nesting:
            self.current_depth += 1
            if self.current_depth > self.MAX_DEPTH:
                self.add_issue(
                    "deep_nesting",
                    f"Nesting depth {self.current_depth} exceeds {self.MAX_DEPTH}",
                    node
                )
        
        super().visit(node)
        
        if is_nesting:
            self.current_depth -= 1
```

---

## 2. Scope Tracking for Unused Detection

### 2.1 Scope Stack

```python
class ScopeTracker:
    """Track variable definitions and usage across scopes"""
    
    def __init__(self):
        self.scopes: list[dict[str, ast.AST]] = [{}]  # Global scope
    
    def push_scope(self):
        """Enter new scope (function, class)"""
        self.scopes.append({})
    
    def pop_scope(self):
        """Exit current scope, return unused definitions"""
        current = self.scopes.pop()
        # Check for unused in this scope
        parent = self.scopes[-1] if self.scopes else {}
        unused = []
        for name, node in current.items():
            if name not in self.used_in_scope(current):
                unused.append((name, node))
        return unused
    
    def define(self, name: str, node: ast.AST):
        """Record variable definition"""
        self.scopes[-1][name] = node
    
    def use(self, name: str):
        """Record variable usage"""
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False
```

### 2.2 Built-in Handling

```python
BUILTINS = {
    'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
    'int', 'str', 'float', 'list', 'dict', 'set', 'tuple',
    'True', 'False', 'None', 'Exception', 'ValueError', ...
}

def is_builtin(name: str) -> bool:
    return name in BUILTINS
```

---

## 3. Nesting Depth Calculation

### 3.1 Depth Tracking

```python
def calculate_max_nesting(tree: ast.AST) -> int:
    """Calculate maximum nesting depth in AST"""
    max_depth = 0
    current_depth = 0
    
    nesting_types = (
        ast.If, ast.For, ast.While, ast.With,
        ast.FunctionDef, ast.AsyncFunctionDef,
        ast.ClassDef, ast.Try, ast.ExceptHandler
    )
    
    for node in ast.walk(tree):
        # This is simplified; actual implementation needs parent tracking
        pass
    
    return max_depth
```

### 3.2 Visitor-Based Depth

The NestingVisitor (shown in section 1.4) uses a stack-based approach:
- Increment depth when entering nesting node
- Decrement when leaving
- Report if depth exceeds threshold

---

## 4. Dataclass Result Schema

### 4.1 Issue Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Issue:
    """A single code issue"""
    type: str                    # 'unused_import', 'unused_var', 'long_function', 'deep_nesting'
    message: str
    line: int
    col: int
    severity: str = 'warning'    # 'error' or 'warning'
```

### 4.2 CheckResult Dataclass

```python
@dataclass
class CheckResult:
    """Complete check results"""
    file_path: str
    issues: list[Issue] = field(default_factory=list)
    
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    def get_by_type(self, issue_type: str) -> list[Issue]:
        return [i for i in self.issues if i.type == issue_type]
    
    @property
    def unused_imports(self) -> list[Issue]:
        return self.get_by_type('unused_import')
    
    @property
    def unused_variables(self) -> list[Issue]:
        return self.get_by_type('unused_var')
    
    @property
    def long_functions(self) -> list[Issue]:
        return self.get_by_type('long_function')
    
    @property
    def deep_nesting(self) -> list[Issue]:
        return self.get_by_type('deep_nesting')
```

### 4.3 Summary Dataclass

```python
@dataclass
class Summary:
    """Summary of all checks"""
    total_files: int
    total_issues: int
    issues_by_type: dict[str, int]
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]PY310` | Python 3.10+ features |
| `[D]STDLIB_ONLY` | Only ast module from stdlib |
| `[MUST]AST_VISITOR` | ast.NodeVisitor subclasses |
| `[!D]NO_REGEX` | No regex; pure AST analysis |
| `[O]DATACLASS` | Issue and CheckResult as dataclasses |
| `[TYPE]FULL_HINTS` | Full type annotations |
| `[CHECK]IMPORT+VAR+LEN+NEST` | Four specific checks implemented |
| `[O]CLASS` | CodeChecker as main class |
| `[FILE]SINGLE` | Single file implementation |

---

## 6. CodeChecker Class

```python
@dataclass
class CodeChecker:
    """Main code checker class"""
    
    def check(self, source: str, filename: str = '<unknown>') -> CheckResult:
        """Check source code for issues"""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return CheckResult(
                file_path=filename,
                issues=[Issue('syntax_error', str(e), e.lineno, e.offset, 'error')]
            )
        
        all_issues = []
        
        # Run all visitors
        visitors = [
            ImportVisitor(),
            VariableVisitor(),
            FunctionLengthVisitor(),
            NestingVisitor()
        ]
        
        for visitor in visitors:
            visitor.visit(tree)
            all_issues.extend(visitor.issues)
        
        return CheckResult(file_path=filename, issues=all_issues)
    
    def check_file(self, path: str) -> CheckResult:
        """Check a file by path"""
        with open(path, 'r') as f:
            source = f.read()
        return self.check(source, path)
```

---

## 7. File Structure

```
MC-PY-04/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── code_checker.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
