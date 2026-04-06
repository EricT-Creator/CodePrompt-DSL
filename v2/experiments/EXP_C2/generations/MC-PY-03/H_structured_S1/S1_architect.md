# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
`\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Matches `{{var}}`, `{{var|filter}}`, `{{var|f1|f2}}`. Group 1 captures the variable name and optional pipe-separated filter chain.

### Conditionals
- Open: `\{%\s*if\s+(.+?)\s*%\}`
- Close: `\{%\s*endif\s*%\}`

Group 1 captures the condition expression.

### Loops
- Open: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
- Close: `\{%\s*endfor\s*%\}`

Group 1 = loop variable, Group 2 = iterable name.

### Master Tokenizer
`\{\{.*?\}\}|\{%.*?%\}`

Splits the template into tag tokens and intervening literal text.

## 2. Parsing Strategy

### Stack-Based Recursive Approach

1. **Tokenize**: Use the master regex to extract all tags. Text segments between tags are literal nodes.
2. **Build tree**: Maintain a stack of "open block" frames:
   - Literal text → `TextNode`
   - `{{ var|filter }}` → `VarNode(name, filters)`
   - `{% if cond %}` → push `IfNode` frame
   - `{% endif %}` → pop `IfNode`, attach as child of current parent
   - `{% for x in items %}` → push `ForNode` frame
   - `{% endfor %}` → pop `ForNode`
3. **Validation**: If the stack is non-empty after all tokens, raise `TemplateSyntaxError` for unclosed blocks.

### AST Node Types

- `TextNode(content: str)`
- `VarNode(name: str, filters: list[str])`
- `IfNode(condition: str, body: list[Node])`
- `ForNode(loop_var: str, iterable: str, body: list[Node])`

Nesting is naturally handled by the stack.

## 3. Filter Pipeline Design

### Filter Registry

A dictionary maps filter names to callables:
- `"upper"` → `str.upper`
- `"lower"` → `str.lower`
- `"capitalize"` → `str.capitalize`

### Execution

Rendering a `VarNode`:
1. Look up variable in context → get raw value
2. Convert to `str`
3. Apply each filter in sequence from left to right
4. If a filter name is not in the registry, raise `TemplateSyntaxError`

## 4. Error Handling Approach

### Custom Exception

`TemplateSyntaxError(Exception)` with a descriptive message.

### Error Matrix

| Situation | Action |
|-----------|--------|
| Unclosed `if`/`for` block | Raise `TemplateSyntaxError` at parse end |
| Unexpected `endif`/`endfor` | Raise `TemplateSyntaxError` immediately |
| Unknown filter | Raise `TemplateSyntaxError` during render |
| Undefined variable | Return empty string (lenient) or raise (strict mode flag) |

### No `ast` Module

Condition evaluation in `{% if %}` uses direct dictionary lookup (truthy check) or simple regex-parsed comparisons (`==`, `!=`). The `ast` module is never imported.

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|-----------|----------------|
| **[L]PY310** | Python 3.10+ features used |
| **[D]STDLIB_ONLY** | Only `re`, `typing` from stdlib |
| **[!D]NO_TMPL_LIB** | No jinja2/mako/etc. |
| **[PARSE]REGEX** | All parsing with `re` module |
| **[!D]NO_AST** | No `ast` module used |
| **[TYPE]FULL_HINTS** | Type hints on all public methods |
| **[ERR]SYNTAX_EXC** | Custom `TemplateSyntaxError` |
| **[O]CLASS** | `TemplateEngine` class |
| **[FILE]SINGLE** | One `.py` file |

## Constraint Checklist

1. [PY310] Target Python 3.10 or later; use only standard library modules.
2. [STDLIB] Do not import jinja2, mako, or any third-party template library.
3. [REGEX] Parse all template constructs using regular expressions from the re module.
4. [NO_AST] Do not use the ast module for expression evaluation or any other purpose.
5. [TYPES] Provide full type annotations on all public methods of the TemplateEngine class.
6. [ERROR] Raise a custom TemplateSyntaxError exception for any malformed template input.
7. [CLASS] Encapsulate all engine logic within a single TemplateEngine class.
8. [FILE] Deliver the complete implementation in a single Python file.
