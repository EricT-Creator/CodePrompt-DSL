# MC-PY-04: Python Code Checker - Technical Design

## Overview

This document outlines the technical design for a Python code checker using AST analysis to detect unused imports, unused variables, long functions, and deep nesting.

## 1. AST Visitor Class Hierarchy

### Base Visitor Structure

```python
import ast
from typing import List, Set, Dict, Optional
from dataclasses import dataclass

class CodeChecker:
    """
    Python code checker using AST analysis.
    
    Checks:
    - Unused imports
    - Unused variables
    - Functions longer than 50 lines
    - Nesting depth exceeding 4 levels
    """
    
    def __init__(self):
        self.issues: List[CheckResult] = []
    
    def check(self, source_code: str) -> List[CheckResult]:
        """Analyze source code and return all issues found."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return [CheckResult(
                check_type="syntax_error",
                line=e.lineno or 0,
                column=e.offset or 0,
                message=str(e),
                severity="error"
            )]
        
        self.issues = []
        self._check_unused_imports(tree)
        self._check_unused_variables(tree)
        self._check_function_length(tree)
        self._check_nesting_depth(tree)
        
        return self.issues
```

### Visitor Pattern

```python
class BaseChecker(ast.NodeVisitor):
    """Base class for AST-based checkers."""
    
    def __init__(self):
        self.issues: List[CheckResult] = []
    
    def check(self, tree: ast.AST) -> List[CheckResult]:
        self.issues = []
        self.visit(tree)
        return self.issues
```

## 2. Scope Tracking for Unused Detection

### Import Tracking

```python
class UnusedImportChecker(BaseChecker):
    """Track all imports and mark them as used when referenced."""
    
    @dataclass
    class ImportInfo:
        name: str
        line: int
        column: int
        is_from_import: bool
    
    def __init__(self):
        super().__init__()
        self.imports: Dict[str, ImportInfo] = {}
        self.used_names: Set[str] = set()
    
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = self.ImportInfo(
                name=name, line=node.lineno,
                column=node.col_offset, is_from_import=False
            )
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = self.ImportInfo(
                name=name, line=node.lineno,
                column=node.col_offset, is_from_import=True
            )
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)
    
    def get_unused(self) -> List[CheckResult]:
        return [
            CheckResult(
                check_type="unused_import",
                line=info.line, column=info.column,
                message=f"Import '{name}' is never used",
                severity="warning"
            )
            for name, info in self.imports.items()
            if name not in self.used_names
        ]
```

### Variable Tracking

```python
class UnusedVariableChecker(BaseChecker):
    """Track variable assignments and detect unread variables."""
    
    @dataclass
    class Scope:
        bindings: Dict[str, int]
        used: Set[str]
    
    def __init__(self):
        super().__init__()
        self.scopes: List[self.Scope] = [self.Scope({}, set())]
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes.append(self.Scope({}, set()))
        self.generic_visit(node)
        
        scope = self.scopes.pop()
        for name, line in scope.bindings.items():
            if name not in scope.used and not name.startswith('_'):
                self.issues.append(CheckResult(
                    check_type="unused_variable",
                    line=line, column=0,
                    message=f"Variable '{name}' is assigned but never used",
                    severity="warning"
                ))
    
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.scopes[-1].bindings[node.id] = node.lineno
        elif isinstance(node.ctx, ast.Load):
            for scope in reversed(self.scopes):
                if node.id in scope.bindings:
                    scope.used.add(node.id)
                    break
        self.generic_visit(node)
```

## 3. Nesting Depth Calculation

```python
class NestingDepthChecker(BaseChecker):
    """Check for nesting depth exceeding threshold."""
    
    NESTING_NODES = (
        ast.If, ast.For, ast.While, ast.With,
        ast.Try, ast.ExceptHandler,
        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
    )
    
    def __init__(self, max_depth: int = 4):
        super().__init__()
        self.max_depth = max_depth
        self.current_depth = 0
    
    def visit(self, node: ast.AST) -> None:
        is_nesting = isinstance(node, self.NESTING_NODES)
        
        if is_nesting:
            self.current_depth += 1
            if self.current_depth > self.max_depth:
                self.issues.append(CheckResult(
                    check_type="deep_nesting",
                    line=getattr(node, 'lineno', 0),
                    column=getattr(node, 'col_offset', 0),
                    message=f"Nesting depth {self.current_depth} exceeds {self.max_depth}",
                    severity="warning"
                ))
        
        self.generic_visit(node)
        
        if is_nesting:
            self.current_depth -= 1
```

## 4. Function Length Check

```python
def _check_function_length(self, tree: ast.AST) -> None:
    """Check for functions exceeding 50 lines."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, 'end_lineno') and node.end_lineno:
                length = node.end_lineno - node.lineno + 1
                if length > 50:
                    self.issues.append(CheckResult(
                        check_type="long_function",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' is {length} lines (max 50)",
                        severity="warning"
                    ))
```

## 5. Dataclass Result Schema

```python
@dataclass
class CheckResult:
    """Result of a code check."""
    check_type: str
    line: int
    column: int
    message: str
    severity: Literal["error", "warning", "info"]
```

## 6. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python 3.10+, standard library only** | Use ast module (standard library) |
| **ast.NodeVisitor or ast.walk** | Implement checkers using ast.NodeVisitor subclass |
| **Dataclass results** | CheckResult dataclass wraps all findings |
| **Full type annotations** | All methods typed with List, Set, Dict, Optional |
| **Four checks implemented** | unused_imports, unused_variables, function_length, nesting_depth |
| **Single Python file** | CodeChecker class with all supporting classes |

## Summary

This design implements a Python code checker using AST analysis. The ast.NodeVisitor pattern enables efficient tree traversal for detecting code issues. Unused import/variable checkers track definitions and usages across scopes. Nesting depth is calculated by tracking entry/exit of control flow nodes. Function length uses the end_lineno attribute when available. All results are wrapped in CheckResult dataclass instances with full type annotations.
