# S3 Auditor — MC-PY-04 (H × RRR)

## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: **PASS** — Python 3.10+ features used (`str | None`, `list[CheckResult]` generics); imports only from stdlib (`ast`, `dataclasses`, `typing`)
- C2 [MUST]AST_VISITOR [!D]NO_REGEX: **PASS** — All checkers use `ast.NodeVisitor` pattern (`ImportChecker(ast.NodeVisitor)`, `VariableChecker(ast.NodeVisitor)`, `FunctionLengthChecker(ast.NodeVisitor)`, `NestingDepthChecker(ast.NodeVisitor)`); no `re` module imported or regex used
- C3 [O]DATACLASS: **PASS** — Result types defined as dataclasses: `@dataclass class CheckResult`, `@dataclass class CheckReport`, `@dataclass class ScopeInfo`
- C4 [TYPE]FULL_HINTS: **PASS** — All function signatures, variables, and return types have type annotations throughout (e.g., `def run(self, tree: ast.Module) -> list[CheckResult]`, `max_line: int = getattr(node, "lineno", 0)`)
- C5 [CHECK]IMPORT+VAR+LEN+NEST: **PASS** — Four checkers implemented: `ImportChecker` (unused imports), `VariableChecker` (unused variables with scope tracking), `FunctionLengthChecker` (functions > 50 lines), `NestingDepthChecker` (nesting > 4 levels)
- C6 [O]CLASS [FILE]SINGLE: **PASS** — Code organized in classes (`CodeChecker`, `ImportChecker`, `VariableChecker`, `FunctionLengthChecker`, `NestingDepthChecker`, dataclasses); all in a single file

## Functionality Assessment (0-5)
Score: 5 — Complete AST-based code checker with four analysis passes: unused import detection (handles aliases and attribute access), unused variable detection (scope-aware with function parameters, tuple unpacking, skip conventions for `_`/`self`/`cls`), function length measurement (using end_lineno), and nesting depth analysis (tracks if/for/while/with/try nesting per function). Orchestrated by `CodeChecker` class with report generation including per-type issue counts. Comprehensive demo with sample code exercising all checkers.

## Corrected Code
No correction needed.
