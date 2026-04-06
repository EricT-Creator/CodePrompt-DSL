# Technical Design: Template Engine (Regex-Based)

## 1. Regex Patterns for Each Template Construct

### Variable Substitution
`\{\{\s*(\w+(?:\|\w+)*)\s*\}\}`

Captures variable name plus optional filter chain. `{{x}}`, `{{x|upper}}`, `{{x|lower|capitalize}}`.

### Conditionals
- Open: `\{%\s*if\s+(.+?)\s*%\}`
- Close: `\{%\s*endif\s*%\}`

### Loops
- Open: `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}`
- Close: `\{%\s*endfor\s*%\}`

### Unified Tokenizer
`\{\{.*?\}\}|\{%.*?%\}`

## 2. Parsing Strategy

### Stack-Based Tree Builder

1. Tokenize the template using the unified regex to separate tags from literal text.
2. Walk through tokens linearly with a frame stack:
   - Literal text → `TextNode` appended to current frame
   - `{{ var|filter }}` → `VarNode` with parsed filter list
   - `{% if cond %}` → push `IfNode` frame
   - `{% endif %}` → pop and validate
   - `{% for x in items %}` → push `ForNode` frame
   - `{% endfor %}` → pop and validate
3. If the stack is non-empty after processing, raise `TemplateSyntaxError`.

### Node Hierarchy

- `TextNode(content: str)`
- `VarNode(name: str, filters: list[str])`
- `IfNode(condition: str, children: list[Node])`
- `ForNode(var_name: str, iterable: str, children: list[Node])`

Nesting is handled by the stack depth.

## 3. Filter Pipeline Design

### Registry

`dict[str, Callable[[str], str]]`:
- `"upper"` → `str.upper`
- `"lower"` → `str.lower`
- `"capitalize"` → `str.capitalize`

### Application

On `VarNode` render: resolve variable → `str()` → apply each filter sequentially. Unknown filter → `TemplateSyntaxError`.

## 4. Error Handling Approach

### TemplateSyntaxError

Custom exception class inheriting from `Exception`, with descriptive messages.

### Triggers

| Error | When |
|-------|------|
| Unclosed block | Stack non-empty at end of parse |
| Orphan closing tag | Stack underflow or type mismatch |
| Unknown filter | Render encounters unregistered name |
| Bad syntax | Regex fails to match expected pattern |

### Condition Evaluation (No `ast`)

`{% if %}` conditions are evaluated by:
- Dictionary lookup for single variable (truthy check)
- Regex-parsed comparisons for `==`, `!=`

The `ast` module is never used.

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | Python 3.10+, stdlib only | `re`, `typing` only |
| 2 | No template libraries | Custom regex-based parser |
| 3 | No `ast` module | Manual expression evaluation |
| 4 | Full type annotations | All public methods annotated |
| 5 | Custom `TemplateSyntaxError` | Raised on all malformed input |
| 6 | Single file, `TemplateEngine` class | One `.py` file |

## Constraint Checklist

1. [PY310] Use Python 3.10 or later with only standard library imports such as re and typing.
2. [NO_TMPL_LIB] Do not import jinja2, mako, or any third-party template rendering library.
3. [REGEX] Implement all template parsing using regular expressions from the re module.
4. [NO_AST] Do not import or use the ast module for expression evaluation or parsing.
5. [TYPE_HINTS] Provide full type annotations on all public methods including parameters and return types.
6. [SYNTAX_ERROR] Raise a custom TemplateSyntaxError for any malformed template including unclosed blocks and unknown filters.
7. [CLASS] Encapsulate all logic in a TemplateEngine class.
8. [SINGLE_FILE] Deliver everything in a single Python file.
