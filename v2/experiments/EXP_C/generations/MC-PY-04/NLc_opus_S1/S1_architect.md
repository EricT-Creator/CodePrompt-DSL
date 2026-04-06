# Technical Design Document — AST-Based Python Code Checker

## 1. Overview

A Python source code analyzer that uses `ast.NodeVisitor` to detect unused imports, unused variables, functions exceeding 50 lines, and nesting depth exceeding 4 levels. Results are returned as `dataclass` instances for structured consumption.

## 2. AST Visitor Class Hierarchy

### Base Design
All analysis is performed by specialized `ast.NodeVisitor` subclasses, each responsible for one type of check. A coordinating `CodeChecker` class runs all visitors and aggregates results.

### Class Hierarchy

#### `CodeChecker`
- The main public class.
- Methods:
  - `check(source: str) -> CheckResult`: parses source into AST, runs all visitors, returns aggregated results.
- Internally creates and runs each visitor against the AST.

#### `ImportVisitor(ast.NodeVisitor)`
- Collects all imported names (from `Import` and `ImportFrom` nodes).
- Records each import's name and line number.
- Output: `set` of imported names with their locations.

#### `NameUsageVisitor(ast.NodeVisitor)`
- Traverses the entire AST to find all `Name` nodes in `Load` context.
- Builds a set of "used names" across the module.
- Used to cross-reference against imports and variable assignments.

#### `VariableVisitor(ast.NodeVisitor)`
- Collects all variable assignments (`Name` nodes in `Store` context).
- Tracks scope (function-level vs. module-level) to avoid false positives.
- Output: `dict` mapping variable names to their assignment locations and scope.

#### `FunctionLengthVisitor(ast.NodeVisitor)`
- Visits `FunctionDef` and `AsyncFunctionDef` nodes.
- Computes function length as `last_line - first_line + 1` using the `end_lineno` attribute (Python 3.8+).
- Flags functions exceeding 50 lines.

#### `NestingDepthVisitor(ast.NodeVisitor)`
- Tracks nesting depth by counting enclosing control-flow structures: `if`, `for`, `while`, `with`, `try`.
- Uses a depth counter incremented on entering a nesting node and decremented on leaving.
- Flags any node where depth exceeds 4.

## 3. Scope Tracking for Unused Detection

### Scope Model
```
Scope {
  name: str                     # e.g., "<module>", "my_function"
  level: "module" | "function"
  imports: dict[str, int]       # name → line number
  assignments: dict[str, int]   # name → line number
  usages: set[str]              # names loaded in this scope
  children: list[Scope]
}
```

### Tracking Strategy

#### Imports (Module Level)
1. `ImportVisitor` collects all imports as `{ name: line }`.
2. `NameUsageVisitor` collects all names used anywhere in the module.
3. Unused imports = `imported_names - used_names`.
4. Special handling: `import x as y` → track `y`, not `x`. `from x import *` → skip (not analyzable statically).

#### Variables (Function Level)
1. `VariableVisitor` enters each function scope and collects assignments.
2. Within the same function scope, collect usages.
3. Unused variables = `assigned_names - used_names` within that scope.
4. Exclusions: variables prefixed with `_` (conventional "unused" marker), loop variables used only for iteration, function parameters (tracked separately if desired).

### Cross-Scope Usage
- A variable assigned in an outer scope and used in an inner scope (closure) should not be flagged. The visitor tracks the full scope tree and propagates usage upward.

## 4. Nesting Depth Calculation Approach

### Definition
Nesting depth = the count of enclosing control-flow structures at any given AST node.

### Counted Structures
- `ast.If` / `ast.IfExp` (conditional)
- `ast.For` / `ast.AsyncFor` (loop)
- `ast.While` (loop)
- `ast.With` / `ast.AsyncWith` (context manager)
- `ast.Try` / `ast.ExceptHandler` (exception handling)

### Algorithm
```python
class NestingDepthVisitor(ast.NodeVisitor):
    current_depth: int = 0
    max_depth: int = 0
    violations: list[NestingIssue] = []

    def _visit_nesting_node(self, node):
        self.current_depth += 1
        if self.current_depth > 4:
            self.violations.append(NestingIssue(line=node.lineno, depth=self.current_depth))
        self.generic_visit(node)
        self.current_depth -= 1

    visit_If = _visit_nesting_node
    visit_For = _visit_nesting_node
    visit_While = _visit_nesting_node
    visit_With = _visit_nesting_node
    visit_Try = _visit_nesting_node
```

### Threshold
- The threshold is 4 levels. Any node at depth > 4 is reported.
- The report includes the line number and the actual depth.

## 5. Dataclass Result Schema

### Result Types

```python
@dataclass
class UnusedImport:
    name: str
    line: int

@dataclass
class UnusedVariable:
    name: str
    line: int
    scope: str  # function name or "<module>"

@dataclass
class LongFunction:
    name: str
    line: int
    length: int  # actual line count

@dataclass
class NestingIssue:
    line: int
    depth: int  # actual nesting depth

@dataclass
class CheckResult:
    unused_imports: list[UnusedImport]
    unused_variables: list[UnusedVariable]
    long_functions: list[LongFunction]
    nesting_issues: list[NestingIssue]
    total_issues: int  # sum of all lists
```

### Usage Pattern
```python
checker = CodeChecker()
result = checker.check(source_code_string)
for issue in result.unused_imports:
    print(f"Line {issue.line}: unused import '{issue.name}'")
```

## 6. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python 3.10+, stdlib only** | All code uses Python standard library. `ast`, `dataclasses`, and `typing` are the only imports. |
| 2 | **ast.NodeVisitor required, no regex** | All source analysis uses `ast.parse` + `ast.NodeVisitor` subclasses. No regex-based source text scanning. |
| 3 | **Results as dataclass** | Every result type (`UnusedImport`, `UnusedVariable`, `LongFunction`, `NestingIssue`, `CheckResult`) is a `@dataclass`. |
| 4 | **Full type annotations** | Every class, method, parameter, and return value is type-annotated. |
| 5 | **Check: unused import/var, long func, deep nest** | Four specific checks are implemented: unused imports, unused variables, functions > 50 lines, nesting > 4 levels. |
| 6 | **Single file, class output** | All visitors, dataclasses, and the `CodeChecker` class reside in one `.py` file. The main deliverable is the `CodeChecker` class. |
