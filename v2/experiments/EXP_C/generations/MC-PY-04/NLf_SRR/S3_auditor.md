## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — Only uses Python standard library modules (`ast`, `sys`, `dataclasses`, `enum`, `typing`). Uses `str | None` syntax requiring Python 3.10+.
- C2 (ast.NodeVisitor, no regex): PASS — Code analysis uses `ast.NodeVisitor` subclasses (`_ImportCollector`, `_NameCollector`, `_ScopeTracker`) and `ast.walk()` in `_check_function_length()`. No `re` or regex patterns are used for code pattern matching.
- C3 (Dataclass results): PASS — All check results are dataclass instances: `@dataclass class CheckResult`, `@dataclass class UnusedImportResult(CheckResult)`, `@dataclass class UnusedVariableResult(CheckResult)`, `@dataclass class FunctionLengthResult(CheckResult)`, `@dataclass class NestingDepthResult(CheckResult)`, `@dataclass class CheckReport`.
- C4 (Full type annotations): PASS — All public methods have type annotations: `check_source(source: str, filename: str = "<string>") -> CheckReport`, `check_file(path: str) -> CheckReport`, `by_type(ct: CheckType) -> list[CheckResult]`, `to_dict() -> dict[str, Any]`.
- C5 (4 checks: import/var/len/nest): PASS — All four checks are implemented: `_check_unused_imports()` detects unused imports, `_check_unused_variables()` via `_ScopeTracker` detects unused variables with scope tracking, `_check_function_length()` flags functions > 50 lines, `_check_nesting_depth()` flags nesting > 4 levels.
- C6 (Single file, class): PASS — All code is in a single file with `CodeChecker` class as the main output.

## Functionality Assessment (0-5)
Score: 5 — Comprehensive static code analyzer with four distinct checks using proper AST visitors. Import checker handles both `import` and `from...import` with alias tracking. Variable checker tracks scopes with function boundaries, handles tuple unpacking, and skips `_` prefixed names. Function length uses `end_lineno` for accuracy. Nesting depth handles async variants and Python 3.11's TryStar. Results have severity levels, line/col info, and serialization.

## Corrected Code
No correction needed.
