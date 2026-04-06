# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
Pattern: `\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Captures the variable name and optional pipe-delimited filter chain. Matches `{{name}}`, `{{name|upper}}`, `{{val|lower|capitalize}}`.

### Conditional Blocks
- Opening tag: `\{%\s*if\s+(.+?)\s*%\}`
- Closing tag: `\{%\s*endif\s*%\}`

Group 1 captures the condition expression string.

### Loop Blocks
- Opening tag: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
- Closing tag: `\{%\s*endfor\s*%\}`

Group 1 = loop variable, Group 2 = iterable name in context.

### Master Tokenizer
`\{\{.*?\}\}|\{%.*?%\}`

This regex splits the entire template into tag tokens, with literal text occupying the gaps between matches.

## 2. Parsing Strategy

### Recursive Stack-Based Approach

The parsing process converts a flat token stream into a tree (AST):

1. **Tokenization**: Apply the master regex via `re.split` or `re.finditer` to separate the template into literals and tags.

2. **Tree construction with a stack**:
   - Start with a root frame on the stack.
   - For each token:
     - Plain text → create `TextNode`, append to top frame's children
     - `{{ expr }}` → parse variable name and filters, create `VarNode`, append to top frame
     - `{% if cond %}` → create `IfNode`, append to top frame, push new frame
     - `{% endif %}` → pop frame; error if it's not an `IfNode`
     - `{% for x in list %}` → create `ForNode`, append to top frame, push new frame
     - `{% endfor %}` → pop frame; error if it's not a `ForNode`
   - After all tokens: if stack has more than the root, raise `TemplateSyntaxError`

3. **Nesting**: The stack naturally handles arbitrary nesting of `if` and `for` blocks.

### Node Types

- `TextNode` — literal content
- `VarNode` — variable reference with optional filter list
- `IfNode` — conditional block with children
- `ForNode` — loop block with loop variable, iterable name, and children

## 3. Filter Pipeline Design

### Filter Registry

A dictionary maps string names to callables:
- `"upper"` → `str.upper`
- `"lower"` → `str.lower`
- `"capitalize"` → `str.capitalize`

### Execution Pipeline

When rendering a `VarNode`:
1. Resolve the variable name from the rendering context
2. Convert the value to a string
3. For each filter in the pipe chain, apply the corresponding function
4. If a filter name is not found in the registry, raise `TemplateSyntaxError`

### Extensibility

Additional filters are added by inserting a new key-value pair into the registry dictionary. No structural changes needed.

## 4. Error Handling Approach

### Custom Exception

`TemplateSyntaxError` extends `Exception`. It carries a descriptive error message including the nature of the syntax problem.

### Error Conditions

| Condition | Behavior |
|-----------|----------|
| Unclosed `{% if %}` | Detected at end of parse; raise `TemplateSyntaxError` |
| Unclosed `{% for %}` | Same as above |
| Orphan `{% endif %}` | Stack underflow or type mismatch; raise immediately |
| Orphan `{% endfor %}` | Same |
| Unknown filter name | Raise during render phase |
| Undefined variable | Return empty string (default) |

### Expression Evaluation Without `ast`

The `{% if cond %}` condition is evaluated without importing the `ast` module. Instead:
- Simple variable names → look up in context, evaluate truthiness
- Comparison expressions (`==`, `!=`, `>`, `<`) → parsed with a small regex and evaluated manually

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | Python 3.10+, stdlib only | Only `re` and `typing` imported |
| 2 | No jinja2/mako/template libs | Custom engine from scratch using regex |
| 3 | No `ast` module | Manual expression evaluation |
| 4 | Full type hints | All public methods annotated |
| 5 | Custom `TemplateSyntaxError` | Raised on all malformed input |
| 6 | Single file, `TemplateEngine` class | One `.py` file with class-based design |
