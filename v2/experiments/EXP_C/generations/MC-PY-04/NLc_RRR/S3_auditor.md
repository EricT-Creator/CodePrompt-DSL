## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — Uses `from __future__ import annotations` and only stdlib imports (ast, dataclasses, typing).
- C2 (ast.NodeVisitor, no regex): PASS — Five visitor classes inherit `ast.NodeVisitor` (ImportVisitor, NameUsageVisitor, VariableVisitor, FunctionLengthVisitor, NestingDepthVisitor); no `import re` in the file.
- C3 (Dataclass results): PASS — All result types are `@dataclass`: `CheckResult`, `UnusedImport`, `UnusedVariable`, `LongFunction`, `NestingIssue`, `ScopeInfo`.
- C4 (Full type annotations): PASS — All functions and methods have type annotations including return types (`-> None`, `-> list[UnusedVariable]`, `-> CheckResult`), parameter types, and class attributes.
- C5 (4 checks: import/var/len/nest): PASS — Implements all four checks: (1) unused imports via ImportVisitor + NameUsageVisitor cross-reference, (2) unused variables via VariableVisitor with scope-aware analysis excluding params and `_`-prefixed names, (3) long functions via FunctionLengthVisitor with configurable max (default 50), (4) deep nesting via NestingDepthVisitor tracking if/for/while/with/try/except depth (default max 4).
- C6 (Single file, class): PASS — Single file with `CodeChecker` class as main entry point containing the `check()` method that orchestrates all visitors.

## Functionality Assessment (0-5)
Score: 5 — Complete static analysis tool with: unused import detection (handles `import` and `from...import`, excludes `*`), scope-aware unused variable detection (excludes parameters and `_`-prefixed), configurable function length checking (uses `end_lineno`), configurable nesting depth checking (covers if/for/async for/while/with/async with/try/except), aggregate issue count via `total_issues` property, graceful handling of syntax errors, and comprehensive demo with sample code covering all check categories.

## Corrected Code
No correction needed.
