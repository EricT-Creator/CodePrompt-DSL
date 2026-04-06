## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS — All imports are from Python stdlib (`ast`, `dataclasses`, `typing`); no third-party libraries.
- C2 [MUST]AST_VISITOR [!D]NO_REGEX: PASS — All four checkers (`ImportChecker`, `VariableChecker`, `FunctionLengthChecker`, `NestingDepthChecker`) extend `ast.NodeVisitor`; no `re` module imported or used.
- C3 [O]DATACLASS: PASS — Data structures use `@dataclass` decorator (`CheckResult`, `CheckReport`, `ScopeInfo`, plus the code also organizes around classes).
- C4 [TYPE]FULL_HINTS: PASS — All functions and methods have complete type hints (e.g., `def check(self, source: str) -> CheckReport`, `def run(self, tree: ast.AST) -> List[CheckResult]`, `def _get_function_lines(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int`).
- C5 [CHECK]IMPORT+VAR+LEN+NEST: PASS — All four check types implemented: `ImportChecker` (unused imports), `VariableChecker` (unused variables), `FunctionLengthChecker` (functions > 50 lines), `NestingDepthChecker` (nesting depth > 4).
- C6 [O]CLASS [FILE]SINGLE: PASS — Code is organized into classes (`CheckResult`, `CheckReport`, `ScopeInfo`, `ImportChecker`, `VariableChecker`, `FunctionLengthChecker`, `NestingDepthChecker`, `CodeChecker`); all in a single file.

## Functionality Assessment (0-5)
Score: 5 — Complete static code checker with: AST-based unused import detection (handles `import` and `from...import`, aliased names), scope-aware unused variable detection (skips `_`-prefixed), function length checker with configurable max, nesting depth checker for control flow structures (if/for/while/with/try/except), aggregate report with issue counts by type, and clean orchestration via `CodeChecker.check()`.

## Corrected Code
No correction needed.
