## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — Imports only from standard library: ast, typing, dataclasses; no third-party packages.
- C2 (ast.NodeVisitor, no regex): PASS — Four visitor classes inherit from `ast.NodeVisitor`: `ImportCollector`, `NameUsageCollector`, `VariableTracker`, `FunctionAnalyzer`; no `import re` or regex patterns in the file.
- C3 (Dataclass results): PASS — All results wrapped in dataclass instances: `UnusedImportIssue`, `UnusedVariableIssue`, `LongFunctionIssue`, `DeepNestingIssue`, `CheckResult`.
- C4 (Full type annotations): PASS — Main public method annotated: `check(self, source: str) -> CheckResult`; all visitor classes have annotated `__init__` and `visit_*` methods.
- C5 (4 checks: import/var/len/nest): PASS — (1) Unused imports via `ImportCollector` + `NameUsageCollector` cross-reference, (2) unused variables via `VariableTracker` with scope tracking, (3) function length >50 via `FunctionAnalyzer._analyze_function()` using `end_lineno - lineno + 1`, (4) nesting depth >4 via `FunctionAnalyzer.generic_visit()` counting nesting constructs.
- C6 (Single file, class): PASS — Single file containing `class CodeChecker:` as main output with supporting visitor classes and dataclasses.

## Functionality Assessment (0-5)
Score: 5 — Comprehensive static code checker with: unused import detection (tracks all imports and cross-references against all Name loads including attribute chains), unused variable detection with scope-aware tracking (per-function scope stack, handles async functions, excludes `_`-prefixed variables, marks for-loop variables as used), function length analysis using AST end_lineno, nesting depth analysis counting 11 nesting construct types (If, IfExp, For, AsyncFor, While, With, AsyncWith, Try, ExceptHandler, FunctionDef, AsyncFunctionDef, ClassDef), proper generic_visit override for depth tracking, and aggregate CheckResult with total issue count and source line count. Well-structured with clean separation of concerns across four specialized visitor classes.

## Corrected Code
No correction needed.
