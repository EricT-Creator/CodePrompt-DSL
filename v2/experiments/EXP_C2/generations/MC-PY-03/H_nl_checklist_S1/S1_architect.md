# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
`\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Captures variable name and optional filter chain separated by `|`. Examples: `{{name}}`, `{{title|upper}}`, `{{x|lower|capitalize}}`.

### Conditional Blocks
- Open: `\{%\s*if\s+(.+?)\s*%\}`
- Close: `\{%\s*endif\s*%\}`

The condition string is captured for later evaluation against the context.

### Loop Blocks
- Open: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
- Close: `\{%\s*endfor\s*%\}`

Group 1 = iteration variable, Group 2 = collection name.

### Unified Tokenizer
`\{\{.*?\}\}|\{%.*?%\}`

Splits the full template into a stream of tag matches interspersed with literal text.

## 2. Parsing Strategy

### Stack-Based Tree Construction

The parser converts the token stream into an AST using a stack:

1. Initialize an empty root node and push it onto the stack.
2. For each token:
   - **Literal text** → append `TextNode(text)` to current stack-top's children
   - **`{{ var|f1|f2 }}`** → append `VarNode(var, [f1, f2])` to current frame
   - **`{% if cond %}`** → create `IfNode(cond)`, append to current frame, push onto stack
   - **`{% endif %}`** → pop stack; if popped node is not an `IfNode`, raise error
   - **`{% for x in items %}`** → create `ForNode(x, items)`, append, push
   - **`{% endfor %}`** → pop; validate it's a `ForNode`
3. After all tokens, if stack has more than the root frame, raise `TemplateSyntaxError`.

### Node Types

- `TextNode(content: str)`
- `VarNode(name: str, filters: list[str])`
- `IfNode(condition: str, children: list[Node])`
- `ForNode(var_name: str, iterable: str, children: list[Node])`

Nested structures are handled naturally by the stack depth.

## 3. Filter Pipeline Design

### Registry Pattern

A `dict[str, Callable[[str], str]]` maps names to functions:
- `"upper"` → `str.upper`
- `"lower"` → `str.lower`
- `"capitalize"` → `str.capitalize`

### Rendering Flow

For a `VarNode` with filters:
1. Resolve variable from context → raw value
2. Cast to `str`
3. Apply each filter left-to-right: `value = registry[filter_name](value)`
4. Unknown filter → raise `TemplateSyntaxError`

### Extensibility

Additional filters can be registered by adding entries to the dictionary.

## 4. Error Handling Approach

### TemplateSyntaxError

Custom exception inheriting from `Exception`. Carries a human-readable message.

### Error Scenarios

| Scenario | Behavior |
|----------|----------|
| Unclosed `{% if %}` | `TemplateSyntaxError("Unclosed if block")` |
| Unclosed `{% for %}` | `TemplateSyntaxError("Unclosed for block")` |
| Orphan `{% endif %}` | `TemplateSyntaxError("Unexpected endif")` |
| Orphan `{% endfor %}` | `TemplateSyntaxError("Unexpected endfor")` |
| Unknown filter | `TemplateSyntaxError("Unknown filter: ...")` |
| Undefined variable | Return empty string or raise based on strict flag |

### No ast Module

Conditional expressions in `{% if %}` are evaluated by:
- Direct dictionary key lookup for truthy/falsy check
- Simple regex-based comparison parsing for `==`/`!=` operators

The `ast` module is never imported or used.

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|-----------|----------------|
| **[L]PY310** | Python 3.10+ with modern syntax |
| **[D]STDLIB_ONLY** | Only `re`, `typing` from standard library |
| **[!D]NO_TMPL_LIB** | No jinja2, mako, or template libraries |
| **[PARSE]REGEX** | All parsing via `re` module |
| **[!D]NO_AST** | `ast` module excluded |
| **[TYPE]FULL_HINTS** | Type annotations on all public methods |
| **[ERR]SYNTAX_EXC** | Custom `TemplateSyntaxError` |
| **[O]CLASS** | `TemplateEngine` class |
| **[FILE]SINGLE** | Single `.py` file |

## Constraint Checklist

1. The implementation must target Python 3.10 or later and use only modules from the Python standard library.
2. The template engine must not import or use jinja2, mako, or any third-party template rendering library, and must instead parse templates entirely through regular expressions.
3. The ast module must not be imported or used for expression evaluation or any other purpose within the engine.
4. Every public method of the TemplateEngine class must have complete type annotations including parameter types and return types.
5. Any malformed template input, including unclosed blocks, orphan closing tags, and unknown filters, must cause the engine to raise a custom TemplateSyntaxError exception with a descriptive message.
6. All engine logic must be encapsulated within a single TemplateEngine class that provides the public rendering interface.
7. The complete implementation must be delivered in a single Python file containing the class definition, the custom exception, and all supporting code.
