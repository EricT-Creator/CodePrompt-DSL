## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS — Uses Python 3.10+ syntax (`list[str]`, `str | Path`, `dict[str, int]`); only stdlib imports (`ast, sys, dataclasses, enum, pathlib, typing`)
- C2 [MUST]AST_VISITOR [!D]NO_REGEX: PASS — Four `ast.NodeVisitor` subclasses (`UnusedImportChecker`, `UnusedVariableChecker`, `FunctionLengthChecker`, `NestingDepthChecker`); no `re` module imported
- C3 [O]DATACLASS: PASS — Uses `@dataclass` for `CheckResult` and `CheckReport`
- C4 [TYPE]FULL_HINTS: PASS — All functions, methods, parameters, and return types fully annotated
- C5 [CHECK]IMPORT+VAR+LEN+NEST: PASS — Four checks implemented: unused imports (via `visit_Import`/`visit_ImportFrom`/`visit_Name`), unused variables (via `visit_FunctionDef` with Store/Load context tracking), function length (line count > 50), nesting depth (> 4 levels)
- C6 [O]CLASS [FILE]SINGLE: PASS — Main logic in `CodeChecker` class; all code in a single file

## Functionality Assessment (0-5)
Score: 5 — Complete AST-based code checker with four distinct checks, severity levels (error/warning/info), dotted attribute resolution for import usage, `_`-prefixed variable convention respect, async function support, configurable thresholds (max lines, max depth), file-based checking, structured report with summary, and comprehensive CLI demo with sample code exercising all four checks.

## Corrected Code
No correction needed.
