## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — Imports are `ast`, `dataclasses`, `typing` (all stdlib). No external packages.
- C2 (ast.NodeVisitor, no regex): PASS — `UnusedImportChecker(ast.NodeVisitor)`, `UnusedVariableChecker(ast.NodeVisitor)`, `NestingDepthChecker(ast.NodeVisitor)` all use `ast.NodeVisitor` with `visit_*` methods. `FunctionLengthChecker` uses `ast.walk(tree)`. No regex for code pattern matching.
- C3 (Dataclass results): PASS — `@dataclass class CheckResult` with `check_type`, `line`, `column`, `message`, `severity` fields. All check results wrapped in `CheckResult` instances.
- C4 (Full type annotations): PASS — All public methods annotated: `check(self, source_code: str) -> List[CheckResult]`, `check_file(self, file_path: str) -> List[CheckResult]`, `format_results(self, results: List[CheckResult], file_name: str = "<stdin>") -> str`.
- C5 (4 checks: import/var/len/nest): PASS — `UnusedImportChecker` (unused imports), `UnusedVariableChecker` (unused variables), `FunctionLengthChecker` (function length > 50), `NestingDepthChecker` (nesting depth > 4). All four checks implemented and invoked in `CodeChecker.check()`.
- C6 (Single file, class): PASS — Single file with `CodeChecker` class as main output.

## Functionality Assessment (0-5)
Score: 5 — Comprehensive AST-based code checker with: unused import detection (handles `import` and `from...import`, tracks attribute chains), unused variable detection (scope-aware with push/pop, ignores `_` prefixed vars, handles function args), function length check (uses `end_lineno`), nesting depth check (tracks If/For/While/With/Try/ExceptHandler), configurable thresholds, file reading support, formatted output, syntax error handling, and sorted results by line number.

## Corrected Code
No correction needed.
