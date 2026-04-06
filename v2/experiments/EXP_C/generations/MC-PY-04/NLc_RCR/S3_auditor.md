## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — Uses only `ast`, `typing`, `dataclasses` — all stdlib; type syntax like `list[UnusedImport]`, `dict[str, int]` requires Python 3.10+.
- C2 (ast.NodeVisitor, no regex): PASS — All analysis done via `ast.NodeVisitor` subclasses (`ImportVisitor`, `NameUsageVisitor`, `VariableVisitor`, `FunctionLengthVisitor`, `NestingDepthVisitor`); no `re` or regex imports.
- C3 (Dataclass results): PASS — All result types are dataclasses: `CheckResult`, `UnusedImport`, `UnusedVariable`, `LongFunction`, `NestingIssue`, all decorated with `@dataclass`.
- C4 (Full type annotations): PASS — All methods and fields have type annotations: `check(self, source: str) -> CheckResult`, `self.imports: dict[str, int]`, `self.used_names: set[str]`, etc.
- C5 (4 checks: import/var/len/nest): PASS — Checks implemented: unused imports (`ImportVisitor` + `NameUsageVisitor`), unused variables (`VariableVisitor`), long functions >50 lines (`FunctionLengthVisitor`), deep nesting >4 levels (`NestingDepthVisitor`).
- C6 (Single file, class): PASS — All classes in one file; main interface is `CodeChecker` class with `check()` method.

## Functionality Assessment (0-5)
Score: 5 — Implements a comprehensive static code checker with: unused import detection (handles `import X`, `from X import Y`, aliased imports, and `import *` exclusion), unused variable detection (scope-aware, ignores `_`-prefixed names), long function detection (configurable threshold at 50 lines, handles both sync and async functions), and deep nesting detection (tracks If/For/While/With/Try nesting beyond depth 4). The visitor pattern is well-structured with clean separation of concerns. The `total_issues` property provides a convenient summary count.

## Corrected Code
No correction needed.
