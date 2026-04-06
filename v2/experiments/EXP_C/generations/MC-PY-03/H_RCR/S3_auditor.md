## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS — All imports are from Python stdlib (`re`, `dataclasses`, `typing`); no third-party libraries.
- C2 [!D]NO_TMPL_LIB [PARSE]REGEX: PASS — No template library imported (no Jinja2, Mako etc.); parsing uses regex patterns (`re.compile`) for tokenization and tag matching (`VAR_PATTERN`, `IF_OPEN`, `FOR_OPEN` etc.).
- C3 [!D]NO_AST: PASS — No `ast` module imported or used; template parsing is done entirely with regex and manual token-based recursive descent.
- C4 [TYPE]FULL_HINTS: PASS — All functions and methods have complete type hints (e.g., `def render(self, template: str, context: Dict[str, Any]) -> str`, `def _parse_tokens(self, tokens: List[tuple[str, str | None]]) -> List[Node]`).
- C5 [ERR]SYNTAX_EXC: PASS — Custom `TemplateSyntaxError(Exception)` is raised for syntax errors (undefined variables, unclosed blocks, invalid tags, unknown filters) with optional line number info.
- C6 [O]CLASS [FILE]SINGLE: PASS — Code is organized into classes (`TemplateSyntaxError`, `TextNode`, `VarNode`, `IfNode`, `ForNode`, `FilterRegistry`, `TemplateEngine`); all in a single file.

## Functionality Assessment (0-5)
Score: 5 — Complete template engine with: variable interpolation (`{{ var }}`), pipe-based filters (upper/lower/capitalize + custom registration), if/else/endif conditionals with ==, !=, and truthiness checks, for/endfor loops, proper nested block handling via stack-based parser, comprehensive syntax error reporting, and clean rendering via recursive node evaluation.

## Corrected Code
No correction needed.
