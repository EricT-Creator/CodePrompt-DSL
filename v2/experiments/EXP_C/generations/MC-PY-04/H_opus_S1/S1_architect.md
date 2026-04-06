# Technical Design Document: AST Code Checker

**Task**: MC-PY-04  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]PY310 [D]STDLIB_ONLY [MUST]AST_VISITOR [!D]NO_REGEX [O]DATACLASS [TYPE]FULL_HINTS [CHECK]IMPORT+VAR+LEN+NEST [O]CLASS [FILE]SINGLE`

---

## 1. AST Visitor Class Hierarchy

### Design

The checker uses Python's `ast` module to parse source code into an AST, then traverses it with custom visitor classes.

### Visitor Hierarchy

```
ast.NodeVisitor                  (stdlib base class)
├── ImportChecker                (detects unused imports)
├── VariableChecker              (detects unused variables)
├── FunctionLengthChecker        (detects functions > 50 lines)
└── NestingDepthChecker          (detects nesting > 4 levels)
```

### Orchestrator

```python
class CodeChecker:
    """Main entry point. Parses source, runs all checkers, returns results."""

    def check(self, source: str) -> CheckReport:
        tree = ast.parse(source)
        results: list[CheckResult] = []
        results.extend(ImportChecker().run(tree))
        results.extend(VariableChecker().run(tree))
        results.extend(FunctionLengthChecker().run(tree))
        results.extend(NestingDepthChecker().run(tree))
        return CheckReport(issues=results, total=len(results))
```

Each checker is independent and produces a list of `CheckResult` dataclass instances. This makes the system modular — new checkers can be added without changing existing ones.

---

## 2. Scope Tracking for Unused Detection

### Import Tracking (ImportChecker)

**Phase 1 — Collection**: Visit `Import` and `ImportFrom` nodes. Record each imported name and its line number.

```python
imported: dict[str, int]  # name → line number
# "import os"        → {"os": 1}
# "from sys import path" → {"path": 2}
# "import os as operating_system" → {"operating_system": 1}
```

**Phase 2 — Usage Detection**: Visit `Name` nodes throughout the entire module. If a `Name.id` matches an imported name, mark it as used.

```python
used_names: set[str]  # populated during full tree traversal
```

**Phase 3 — Report**: Any name in `imported` that is not in `used_names` is an unused import.

### Variable Tracking (VariableChecker)

**Scope-aware tracking** is necessary because a variable defined in one function can shadow a module-level variable.

**Scope Stack**:

```python
scopes: list[ScopeInfo]

@dataclass
class ScopeInfo:
    name: str                              # function/class/module name
    defined: dict[str, int]                # var_name → line number
    used: set[str]                         # var names read
```

**Visitor Behavior**:

| Node Type | Action |
|-----------|--------|
| `FunctionDef` / `AsyncFunctionDef` | Push new scope |
| `ClassDef` | Push new scope |
| End of function/class body | Pop scope, check for unused |
| `Assign` target `Name` | Add to current scope's `defined` |
| `AnnAssign` target `Name` | Add to current scope's `defined` |
| `Name` in `Load` context | Add to current scope's `used` |

**Special cases**:
- Variables starting with `_` are conventionally ignored (private/intentionally unused).
- `__all__`, `__init__`, and dunder methods are excluded.
- Function parameters are tracked as defined but only flagged if truly unused within the body.

---

## 3. Nesting Depth Calculation Approach

### Definition

Nesting depth is the maximum level of nested control-flow structures within a function:

```python
def example():           # depth 0
    if cond:             # depth 1
        for x in xs:     # depth 2
            if x > 0:    # depth 3
                while y:  # depth 4
                    pass   # depth 5 → VIOLATION (> 4)
```

### Nesting-Increasing Nodes

```python
NESTING_NODES = {
    ast.If, ast.For, ast.While, ast.AsyncFor,
    ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler
}
```

### Algorithm

```python
class NestingDepthChecker(ast.NodeVisitor):
    current_depth: int = 0
    max_depth: int = 0
    function_name: str = ""

    def visit_FunctionDef(self, node):
        self.function_name = node.name
        self.current_depth = 0
        self.max_depth = 0
        self.generic_visit(node)
        if self.max_depth > 4:
            self.report(node)

    def visit_If(self, node):   # (same for For, While, etc.)
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1
```

The depth counter increments on entering a nesting node and decrements on leaving. The maximum is tracked per function.

---

## 4. Dataclass Result Schema

### CheckResult

```python
@dataclass
class CheckResult:
    check_type: Literal["unused_import", "unused_variable", "long_function", "deep_nesting"]
    message: str
    line: int
    column: int
    severity: Literal["warning", "error"]
    context: str             # e.g., function name, import name
```

### CheckReport

```python
@dataclass
class CheckReport:
    issues: list[CheckResult]
    total: int
    by_type: dict[str, int]   # count per check_type

    def __post_init__(self) -> None:
        self.by_type = {}
        for issue in self.issues:
            self.by_type[issue.check_type] = self.by_type.get(issue.check_type, 0) + 1
```

### Example Output

```python
CheckResult(
    check_type="unused_import",
    message="Import 'os' is imported but never used",
    line=1,
    column=0,
    severity="warning",
    context="os"
)

CheckResult(
    check_type="deep_nesting",
    message="Function 'process_data' has nesting depth 6 (max allowed: 4)",
    line=15,
    column=0,
    severity="warning",
    context="process_data"
)
```

### Thresholds

| Check | Threshold | Severity |
|-------|-----------|----------|
| Unused import | Any unused | warning |
| Unused variable | Any unused (except `_` prefixed) | warning |
| Long function | > 50 lines | warning |
| Deep nesting | > 4 levels | warning |

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Python 3.10+ | `[L]PY310` | Uses Python 3.10 type syntax, `match` statement (optional), `X \| Y` unions. |
| Stdlib only | `[D]STDLIB_ONLY` | Only `ast`, `typing`, `dataclasses` from stdlib. No external packages. |
| Must use AST visitor | `[MUST]AST_VISITOR` | All four checkers extend `ast.NodeVisitor` and traverse the parsed AST. |
| No regex | `[!D]NO_REGEX` | No `re` module. All pattern detection is done via AST node types and attributes. |
| Dataclass output | `[O]DATACLASS` | `CheckResult`, `CheckReport`, `ScopeInfo` are all `@dataclass` classes. |
| Full type hints | `[TYPE]FULL_HINTS` | Every function, method, variable, and return type is fully annotated with type hints. |
| Four checks: import + var + len + nest | `[CHECK]IMPORT+VAR+LEN+NEST` | Four dedicated visitor classes: `ImportChecker`, `VariableChecker`, `FunctionLengthChecker`, `NestingDepthChecker`. |
| Class-based output | `[O]CLASS` | `CodeChecker` orchestrator and all checker visitors are classes. |
| Single file | `[FILE]SINGLE` | All classes and logic in one `.py` file. |
