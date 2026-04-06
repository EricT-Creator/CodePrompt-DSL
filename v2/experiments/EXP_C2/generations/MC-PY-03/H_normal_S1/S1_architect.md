# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
Pattern: `\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Captures the variable name and optional filter chain. Example matches: `{{name}}`, `{{name|upper}}`, `{{title|lower|capitalize}}`.

### Conditionals
Opening: `\{%\s*if\s+(.+?)\s*%\}`
Closing: `\{%\s*endif\s*%\}`

The condition expression (captured group 1) is evaluated against the context dictionary. Supports simple truthy checks and basic comparisons.

### For Loops
Opening: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
Closing: `\{%\s*endfor\s*%\}`

Captures the loop variable name (group 1) and the iterable name (group 2).

### Filter Pipes
Handled within the variable pattern above. The pipe character `|` separates the variable from filter names. Multiple filters are chained left-to-right.

### Master Tokenizer
A single tokenizer regex splits the template into segments:

`\{\{.*?\}\}|\{%.*?%\}`

This matches any `{{ ... }}` or `{% ... %}` block. Text between matches is literal content.

## 2. Parsing Strategy

### Recursive Descent with Stack

The engine uses a **stack-based recursive approach**:

1. **Tokenize**: Split the template into a flat list of tokens (literal text, variable, if-open, endif, for-open, endfor).
2. **Build AST**: Walk the token list with a stack:
   - On literal text → push a `TextNode`
   - On `{{ var }}` → push a `VarNode` (with optional filters)
   - On `{% if %}` → push an `IfNode` frame onto the stack; subsequent tokens become its children
   - On `{% endif %}` → pop the `IfNode` frame, finalize it, attach to parent
   - On `{% for %}` → push a `ForNode` frame
   - On `{% endfor %}` → pop the `ForNode` frame
3. **Nesting**: The stack naturally handles nested `if`/`for` structures. If the stack is non-empty after processing all tokens, raise `TemplateSyntaxError`.

### Node Types

- `TextNode(content: str)`
- `VarNode(name: str, filters: list[str])`
- `IfNode(condition: str, children: list[Node])`
- `ForNode(var_name: str, iterable_name: str, children: list[Node])`

## 3. Filter Pipeline Design

### Registry

A `dict[str, Callable[[str], str]]` maps filter names to functions:

- `upper` → `str.upper`
- `lower` → `str.lower`
- `capitalize` → `str.capitalize`

### Application

When rendering a `VarNode`:
1. Resolve the variable from context
2. Convert to string
3. For each filter in the chain, look up the function in the registry and apply it sequentially

### Extensibility

New filters can be added by inserting into the registry dictionary. The architecture supports this without changes to the parser.

## 4. Error Handling Approach

### Custom Exception

A `TemplateSyntaxError` exception is defined, inheriting from `Exception`. It carries a message describing the location and nature of the error.

### Error Conditions

| Condition | Response |
|-----------|----------|
| Unmatched `{% endif %}` | Raise `TemplateSyntaxError("Unexpected endif")` |
| Unmatched `{% endfor %}` | Raise `TemplateSyntaxError("Unexpected endfor")` |
| Unclosed `{% if %}` block | Raise at end of parse if stack non-empty |
| Unclosed `{% for %}` block | Same as above |
| Unknown filter name | Raise `TemplateSyntaxError("Unknown filter: xxx")` |
| Undefined variable | Return empty string or raise, depending on strict mode |

### No `ast` Module

Expression evaluation for `{% if %}` conditions is handled by simple string matching against the context dictionary (truthy check) or basic regex-based comparison parsing — never via `ast.literal_eval` or `ast.parse`.

## 5. Constraint Acknowledgment

| Constraint | How Addressed |
|-----------|---------------|
| **[L]PY310** | Python 3.10+ with match-case and modern syntax |
| **[D]STDLIB_ONLY** | Only standard library imports (re, typing, etc.) |
| **[!D]NO_TMPL_LIB** | No jinja2, mako, or any template library |
| **[PARSE]REGEX** | All parsing via `re` module regex patterns |
| **[!D]NO_AST** | No `ast` module for expression evaluation |
| **[TYPE]FULL_HINTS** | Full type annotations on all public methods |
| **[ERR]SYNTAX_EXC** | Custom `TemplateSyntaxError` for malformed templates |
| **[O]CLASS** | Single `TemplateEngine` class encapsulates all logic |
| **[FILE]SINGLE** | Everything in one `.py` file |
