## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS — Uses only stdlib modules (`ast`, `sys`, `dataclasses`, `typing`). Syntax compatible with Python 3.10+ via `from __future__ import annotations`.
- C2 [MUST]AST_VISITOR [!D]NO_REGEX: PASS — All analysis performed via `ast.NodeVisitor` subclasses (`ImportVisitor`, `VariableVisitor`, `FunctionLengthVisitor`, `NestingVisitor`). No `re` module imported.
- C3 [O]DATACLASS: PASS — Core data models use `@dataclass` decorator: `Issue`, `CheckResult`, `Summary`, `CodeChecker`.
- C4 [TYPE]FULL_HINTS: PASS — All functions and methods have complete type annotations (e.g., `def check(self, source: str, filename: str = "<unknown>") -> CheckResult`, `def finalize(self) -> None`).
- C5 [CHECK]IMPORT+VAR+LEN+NEST: PASS — Four check types implemented: unused imports (`ImportVisitor` tracks imports vs. used names), unused variables (`VariableVisitor` with scope stack), function length (`FunctionLengthVisitor` with configurable max lines), nesting depth (`NestingVisitor` tracking depth through If/For/While/With/Try/ExceptHandler nodes).
- C6 [O]CLASS [FILE]SINGLE: PASS — Core logic in classes (`CodeChecker`, four visitor classes). All code in a single file.

## Functionality Assessment (0-5)
Score: 5 — Complete AST-based code checker with: four distinct analysis passes (unused imports, unused variables, function length, nesting depth), configurable thresholds, scope-aware variable tracking, support for async functions, comprehensive builtins whitelist, multi-file batch checking with summary, sorted output by line/column, severity levels, and a working demo with sample code demonstrating all check types.

## Corrected Code
No correction needed.
