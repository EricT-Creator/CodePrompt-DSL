# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
`\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Matches `{{var}}`, `{{var|filter1}}`, `{{var|f1|f2}}`. Group 1 captures the full expression including pipe-separated filters.

### Conditional Blocks
- Opening: `\{%\s*if\s+(.+?)\s*%\}`
- Closing: `\{%\s*endif\s*%\}`

### Loop Blocks
- Opening: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
- Closing: `\{%\s*endfor\s*%\}`

### Tokenizer
`\{\{.*?\}\}|\{%.*?%\}`

Splits the template into a sequence of tags and literal text segments.

## 2. Parsing Strategy

### Stack-Based Tree Builder

1. **Tokenize**: Use `re.finditer` with the unified tokenizer to identify all tag positions. Everything between tags is literal text.

2. **Build AST**:
   - Maintain a stack initialized with a root container node.
   - For each token:
     - Literal text → `TextNode`, appended to stack-top's children
     - `{{ expr }}` → parse into `VarNode(name, filters)`, append to stack-top
     - `{% if cond %}` → create `IfNode`, append to stack-top, push onto stack
     - `{% endif %}` → pop from stack; validate popped node is `IfNode`
     - `{% for x in items %}` → create `ForNode`, append, push
     - `{% endfor %}` → pop; validate `ForNode`
   - Post-processing: if stack depth > 1, raise `TemplateSyntaxError` for unclosed blocks

### Node Types

- `TextNode(content: str)` — plain text
- `VarNode(name: str, filters: list[str])` — variable with filter chain
- `IfNode(condition: str, children: list[Node])` — conditional block
- `ForNode(var_name: str, iterable: str, children: list[Node])` — iteration block

Arbitrary nesting depth is supported by the stack mechanism.

## 3. Filter Pipeline Design

### Filter Registry

A dictionary mapping filter names to callables:
- `"upper"` → `str.upper`
- `"lower"` → `str.lower`
- `"capitalize"` → `str.capitalize`

### Pipeline Execution

When rendering a `VarNode`:
1. Resolve `name` from the rendering context dictionary
2. Convert to `str`
3. For each filter in the list: `value = registry[filter_name](value)`
4. If a filter is not in the registry, raise `TemplateSyntaxError`

New filters are added by inserting entries into the registry dict.

## 4. Error Handling Approach

### Custom Exception

`TemplateSyntaxError` inherits from `Exception` and carries a descriptive message.

### Error Catalogue

| Condition | Response |
|-----------|----------|
| Unclosed `if` or `for` block | Raise at end of parsing |
| Unexpected `endif` or `endfor` | Raise immediately (stack mismatch) |
| Unknown filter in pipe | Raise during render |
| Malformed tag syntax | Raise during tokenization |

### Expression Evaluation Without `ast`

`{% if cond %}` conditions are evaluated through:
- Simple variable lookup: `bool(context.get(cond_var))`
- Basic comparison: regex parse for `var == "value"` or `var != "value"`, then manual comparison

The `ast` module is never imported.

## 5. Constraint Acknowledgment

| # | Constraint | How Addressed |
|---|-----------|---------------|
| 1 | Python 3.10+, stdlib only | Only `re`, `typing` used |
| 2 | No template libraries | Hand-built regex parser |
| 3 | No `ast` module | Manual condition evaluation |
| 4 | Full type annotations | Every public method annotated |
| 5 | `TemplateSyntaxError` | Custom exception for all error cases |
| 6 | Single file, class-based | One `.py`, `TemplateEngine` class |

## Constraint Checklist

1. The implementation must use Python 3.10 or later and only import modules from the Python standard library, with no external dependencies whatsoever.
2. Jinja2, Mako, and any other third-party template rendering library must not be imported or used; the template parsing must be built from scratch using regular expressions.
3. The ast module must not be imported or invoked for expression evaluation, template parsing, or any other purpose.
4. All public methods of the TemplateEngine class must carry complete type annotations specifying both parameter types and return types.
5. Whenever the engine encounters a malformed template, including unclosed blocks, mismatched closing tags, or unrecognized filters, it must raise a custom TemplateSyntaxError exception with a message describing the problem.
6. All template engine functionality must be organized within a single TemplateEngine class that serves as the sole public interface.
7. The entire implementation, including the class, the custom exception, and any helper utilities, must be delivered in a single Python file.
