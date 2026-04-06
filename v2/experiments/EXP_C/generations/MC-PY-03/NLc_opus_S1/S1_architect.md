# Technical Design Document — Template Engine

## 1. Overview

A regex-based template engine supporting variable substitution (`{{var}}`), conditionals (`{% if %}...{% endif %}`), loops (`{% for item in list %}...{% endfor %}`), filter pipes (`{{var|filter}}`), and nested control structures. Parsing uses regex and a stack-based approach without the `ast` module.

## 2. Regex Patterns for Each Template Construct

### Variable Substitution
```
\{\{\s*(\w+(?:\|\w+)*)\s*\}\}
```
Matches `{{var}}` and `{{var|filter1|filter2}}`. Captures the full expression including pipe-separated filter chain.

### If Block (opening)
```
\{%\s*if\s+(.+?)\s*%\}
```
Captures the condition expression.

### Endif
```
\{%\s*endif\s*%\}
```

### For Block (opening)
```
\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}
```
Captures the loop variable name and the iterable name.

### Endfor
```
\{%\s*endfor\s*%\}
```

### Combined Tokenizer Pattern
A single combined regex with alternation tokenizes the entire template in one pass:
```
(
  \{\{.*?\}\}        |  # variable
  \{%\s*if\s+.*?%\}  |  # if open
  \{%\s*endif\s*%\}   |  # endif
  \{%\s*for\s+.*?%\}  |  # for open
  \{%\s*endfor\s*%\}      # endfor
)
```
Text between tokens is captured as literal text nodes.

## 3. Parsing Strategy — Stack-Based

### Token Types
- `TEXT`: literal string content.
- `VAR`: a variable reference, possibly with filters.
- `IF_OPEN`: opens a conditional block.
- `ENDIF`: closes a conditional block.
- `FOR_OPEN`: opens a loop block.
- `ENDFOR`: closes a loop block.

### AST Node Types
- `TextNode(content: str)`
- `VarNode(name: str, filters: list[str])`
- `IfNode(condition: str, body: list[Node])`
- `ForNode(var_name: str, iterable_name: str, body: list[Node])`

### Stack-Based Parsing Algorithm

1. Tokenize the template string using the combined regex, producing a flat list of tokens.
2. Initialize a stack with a single root `BlockNode` (the document).
3. Iterate through tokens:
   - `TEXT` / `VAR`: append to the current top-of-stack node's children.
   - `IF_OPEN`: create an `IfNode`, append it to the current node's children, push the `IfNode` onto the stack (it becomes the current parent).
   - `FOR_OPEN`: same pattern — create a `ForNode`, append, push.
   - `ENDIF`: pop the stack. If the popped node is not an `IfNode`, raise `TemplateSyntaxError`.
   - `ENDFOR`: pop the stack. If the popped node is not a `ForNode`, raise `TemplateSyntaxError`.
4. After all tokens are processed, the stack should contain only the root node. If not, raise `TemplateSyntaxError` for unclosed blocks.

### Nested Structures
The stack naturally handles arbitrary nesting: a `for` inside an `if` pushes `ForNode` on top of `IfNode`. Closing tags pop in reverse order, ensuring correct structure.

## 4. Rendering (Evaluation)

### Tree Walking
A recursive `render(node, context)` function:
- `TextNode`: return its content string.
- `VarNode`: look up `name` in context, apply filters in sequence, return the string result.
- `IfNode`: evaluate `condition` against the context (truthy check); if true, render body nodes; if false, return empty string.
- `ForNode`: look up `iterable_name` in context, iterate; for each item, create a child context with `var_name → item`, render body nodes, concatenate.

### Condition Evaluation
- Simple truthy check: resolve the condition name from context; Python's truthiness rules apply (empty string, None, 0, empty list = false).
- No complex expression parsing (no `and/or/not` operators). This is a design simplification; conditions are single variable checks.

## 5. Filter Pipeline Design

### Built-in Filters
| Filter | Behavior |
|--------|----------|
| `upper` | `str.upper()` |
| `lower` | `str.lower()` |
| `capitalize` | `str.capitalize()` |

### Filter Registry
```python
FILTERS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
}
```

### Application
For `{{var|upper|capitalize}}`:
1. Resolve `var` from context → raw value.
2. Convert to string: `str(raw)`.
3. Apply `upper` → result1.
4. Apply `capitalize` → result2.
5. Return result2.

Filters are applied left to right. An unknown filter name raises `TemplateSyntaxError`.

## 6. Error Handling Approach

### TemplateSyntaxError
A custom exception raised for:
- Unclosed `{% if %}` or `{% for %}` blocks (stack not empty after parsing).
- Mismatched closing tags (`{% endif %}` when top of stack is `ForNode`).
- Unknown filter names in variable expressions.
- Malformed tag syntax that doesn't match any regex pattern.

### Runtime Errors
- Missing variable in context: can either return an empty string (lenient mode) or raise `TemplateSyntaxError` (strict mode). Default: lenient with a warning.
- Non-iterable value in `{% for %}`: raise `TemplateSyntaxError` with a descriptive message.

### Error Messages
Each error includes the approximate position in the template (token index or character offset) to aid debugging.

## 7. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python 3.10+, stdlib only** | All code uses only Python standard library. `re` for regex, `dataclasses` for node types. |
| 2 | **Regex parsing, no jinja2/mako** | Template tokenization and pattern matching use `re` module exclusively. No template library dependencies. |
| 3 | **No ast module** | The `ast` module is not imported or used. Condition evaluation uses simple context lookup and truthiness, not `ast.literal_eval` or `ast.parse`. |
| 4 | **Full type annotations** | Every class, function, parameter, and return value is fully type-annotated. |
| 5 | **TemplateSyntaxError on errors** | A custom `TemplateSyntaxError` exception class is defined and raised for all parsing and rendering errors. |
| 6 | **Single file, class output** | All classes (`TemplateEngine`, node types, error class, filter registry) reside in one `.py` file. The main deliverable is the `TemplateEngine` class. |
