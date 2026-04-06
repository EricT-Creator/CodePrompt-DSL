You are a developer. Implement the technical design below as a single Python file (.py). Follow ALL engineering constraints listed below strictly. Output code only, no explanation.

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Must use ast.NodeVisitor or ast.walk for code analysis. Do not use regular expressions for code pattern matching.
3. Wrap all check results in dataclass instances.
4. Full type annotations on all public methods.
5. Implement all four checks: unused imports, unused variables, function length > 50 lines, nesting depth > 4.
6. Deliver a single Python file with a CodeChecker class.

Technical Design:
---
# Technical Design Document — AST Code Checker

## 1. Overview

This document describes the architecture for a Python code checker that accepts source code as a string and performs four checks: unused imports, unused variables, functions longer than 50 lines, and nesting depth exceeding 4 levels. The checker uses `ast.NodeVisitor` or `ast.walk` for code analysis and returns results as dataclass instances.

## 2. AST Visitor Class Hierarchy

### 2.1 Design

The checker uses a layered visitor approach. A primary `CodeChecker` class orchestrates the analysis, delegating to specialized visitor classes for each check type.

### 2.2 Visitor Classes

| Visitor | Inherits | Purpose |
|---------|----------|---------|
| `ImportCollector` | `ast.NodeVisitor` | Walks the AST to collect all import names and their line numbers |
| `NameUsageCollector` | `ast.NodeVisitor` | Walks the AST to collect all name references (loads) in non-import contexts |
| `VariableTracker` | `ast.NodeVisitor` | Tracks variable assignments (stores) and usages per scope |
| `FunctionAnalyzer` | `ast.NodeVisitor` | Visits function definitions to calculate line count and nesting depth |

### 2.3 CodeChecker Class

The main orchestrator:

- `CodeChecker()` — Constructor.
- `check(source: str) -> CheckResult` — Parse source, run all visitors, aggregate results.
- `check_unused_imports(tree: ast.Module) -> list[UnusedImportIssue]`
- `check_unused_variables(tree: ast.Module) -> list[UnusedVariableIssue]`
- `check_long_functions(tree: ast.Module) -> list[LongFunctionIssue]`
- `check_deep_nesting(tree: ast.Module) -> list[DeepNestingIssue]`

## 3. Scope Tracking for Unused Detection

### 3.1 Import Tracking

1. **ImportCollector** visits `ast.Import` and `ast.ImportFrom` nodes.
2. For each imported name (including aliases), records `{ name: str, alias: str | None, line: int, module: str | None }`.
3. Builds a set of all imported names (using alias if present, original name otherwise).

### 3.2 Name Usage Collection

1. **NameUsageCollector** visits `ast.Name` nodes where `ctx` is `ast.Load`.
2. Also visits `ast.Attribute` nodes to catch `module.func` usage patterns.
3. Builds a set of all referenced names.

### 3.3 Unused Import Detection

Imported names that do not appear in the usage set are flagged as unused. Special handling:
- `__all__` references are considered usage.
- Names starting with `_` are optionally excluded (convention for private imports).
- `import *` is flagged as a separate warning.

### 3.4 Variable Scope Tracking

1. **VariableTracker** maintains a scope stack. Each scope is a dictionary mapping variable names to `{ assigned: bool, used: bool, line: int }`.
2. On entering a function or class, push a new scope.
3. On `ast.Name` with `ctx == ast.Store`: mark as assigned in current scope.
4. On `ast.Name` with `ctx == ast.Load`: mark as used in current scope (or parent scopes via lookup).
5. On exiting a scope, any name that is assigned but never used (and not prefixed with `_`) is flagged.

### 3.5 Exclusions

- Loop variables (`for x in ...`) are tracked but only flagged if truly unused within the loop body.
- Function parameters are tracked as assigned at function entry.
- Variables named `_` are conventionally excluded.

## 4. Nesting Depth Calculation Approach

### 4.1 Method

**FunctionAnalyzer** tracks nesting depth by incrementing a counter when entering nesting constructs and decrementing when leaving.

### 4.2 Nesting Constructs

The following AST node types increment the depth:
- `ast.If` / `ast.IfExp`
- `ast.For` / `ast.AsyncFor`
- `ast.While`
- `ast.With` / `ast.AsyncWith`
- `ast.Try` / `ast.ExceptHandler`
- `ast.FunctionDef` / `ast.AsyncFunctionDef` (nested functions)
- `ast.ClassDef` (nested classes)

### 4.3 Tracking

1. Override `visit()` to intercept all node types.
2. For nesting constructs, increment `current_depth` before visiting children, decrement after.
3. Track `max_depth` per function.
4. If `max_depth > 4`, flag the function.

### 4.4 Function Length Calculation

For each `ast.FunctionDef` / `ast.AsyncFunctionDef`:
- `length = node.end_lineno - node.lineno + 1` (Python 3.8+ provides `end_lineno`).
- If `length > 50`, flag the function.

## 5. Dataclass Result Schema

### 5.1 Issue Dataclasses

```
@dataclass
class UnusedImportIssue:
    name: str
    line: int
    module: str | None

@dataclass
class UnusedVariableIssue:
    name: str
    line: int
    scope: str  # function name or "<module>"

@dataclass
class LongFunctionIssue:
    function_name: str
    line: int
    length: int
    threshold: int  # 50

@dataclass
class DeepNestingIssue:
    function_name: str
    line: int
    max_depth: int
    threshold: int  # 4
```

### 5.2 Aggregate Result

```
@dataclass
class CheckResult:
    unused_imports: list[UnusedImportIssue]
    unused_variables: list[UnusedVariableIssue]
    long_functions: list[LongFunctionIssue]
    deep_nesting: list[DeepNestingIssue]
    total_issues: int
    source_lines: int
```

`total_issues` is computed as the sum of all four issue lists' lengths.

## 6. Usage Flow

1. Instantiate `CodeChecker()`.
2. Call `checker.check(source_code_string)`.
3. Internally:
   a. Parse source to AST: `tree = ast.parse(source)`.
   b. Run `ImportCollector` and `NameUsageCollector` → unused imports.
   c. Run `VariableTracker` → unused variables.
   d. Run `FunctionAnalyzer` → long functions and deep nesting.
4. Return `CheckResult` dataclass with all findings.

## 7. Error Handling

- If `ast.parse()` fails (syntax error in the source), raise a descriptive error or return a `CheckResult` with a parse error flag.
- Individual check visitors are isolated — a failure in one check does not prevent others from running.

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python 3.10+, standard library only | Only `ast`, `typing`, and `dataclasses` from stdlib are used. No external packages. |
| 2 | Must use ast.NodeVisitor or ast.walk; no regex for code patterns | All four checks use `ast.NodeVisitor` subclasses to traverse the AST. No regex is used for code pattern matching. |
| 3 | Wrap check results in dataclass instances | `UnusedImportIssue`, `UnusedVariableIssue`, `LongFunctionIssue`, `DeepNestingIssue`, and `CheckResult` are all `@dataclass` classes. |
| 4 | Full type annotations on all public methods | All public methods of `CodeChecker` and all visitor classes have complete type annotations for parameters and return types. |
| 5 | Implement all four checks | Unused imports, unused variables, function length > 50 lines, and nesting depth > 4 are all implemented as described. |
| 6 | Single Python file with CodeChecker class | All visitor classes, dataclasses, and the `CodeChecker` orchestrator are in one `.py` file. |
---
