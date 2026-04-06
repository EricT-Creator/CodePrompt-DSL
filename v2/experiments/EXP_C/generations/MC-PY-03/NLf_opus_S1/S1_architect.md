# Technical Design Document — Template Engine

## 1. Overview

This document describes the architecture for a template engine that supports `{{var}}` variable substitution, `{% if cond %}...{% endif %}` conditionals, `{% for item in list %}...{% endfor %}` loops, `{{var|filter}}` filter pipes (supporting at least upper, lower, capitalize), and nested if/for structures. Templates are parsed using regular expressions, and a custom `TemplateSyntaxError` is raised for malformed input.

## 2. Regex Patterns for Each Template Construct

### 2.1 Pattern Inventory

| Construct | Pattern | Description |
|-----------|---------|-------------|
| Variable | `\{\{\\s*([a-zA-Z_][a-zA-Z0-9_.]*(?:\\|[a-zA-Z_]+)*)\\s*\}\}` | Matches `{{var}}` or `{{var\|filter}}` or `{{var\|f1\|f2}}` |
| If open | `\{%\\s*if\\s+(.+?)\\s*%\}` | Matches `{% if condition %}` |
| Else | `\{%\\s*else\\s*%\}` | Matches `{% else %}` |
| Endif | `\{%\\s*endif\\s*%\}` | Matches `{% endif %}` |
| For open | `\{%\\s*for\\s+(\\w+)\\s+in\\s+(\\w+)\\s*%\}` | Matches `{% for item in list %}` |
| Endfor | `\{%\\s*endfor\\s*%\}` | Matches `{% endfor %}` |
| Any tag | `\{\{.+?\}\}\|\{%.+?%\}` | Tokenizer pattern to split template into text and tag tokens |

### 2.2 Tokenization

The template string is split into a token stream by scanning for `{{ ... }}` and `{% ... %}` patterns. Text between tags becomes `TEXT` tokens. The tokenizer preserves order and captures the full match for each tag.

## 3. Parsing Strategy

### 3.1 Recursive Descent with Stack

The parser uses a stack-based approach to handle nesting:

1. **Tokenize**: Split the template into a flat list of tokens: `TEXT`, `VAR`, `IF`, `ELSE`, `ENDIF`, `FOR`, `ENDFOR`.
2. **Parse**: Walk the token list with a recursive descent parser.
   - On `TEXT`: create a `TextNode`.
   - On `VAR`: create a `VarNode` (with optional filter chain).
   - On `IF`: push a new `IfNode` onto the parsing stack. Recursively parse the body until `ELSE` or `ENDIF`.
   - On `ELSE`: switch to the else-branch of the current `IfNode`.
   - On `ENDIF`: pop the `IfNode` from the stack, finalize it.
   - On `FOR`: push a new `ForNode`. Recursively parse the body until `ENDFOR`.
   - On `ENDFOR`: pop the `ForNode`.
3. **Validate**: After parsing, if the stack is non-empty (unclosed blocks), raise `TemplateSyntaxError`.

### 3.2 AST Nodes

- **TextNode**: `{ content: str }` — Raw text, output as-is.
- **VarNode**: `{ name: str; filters: list[str] }` — Variable lookup with optional filter chain.
- **IfNode**: `{ condition: str; body: list[Node]; else_body: list[Node] }` — Conditional block.
- **ForNode**: `{ var_name: str; iterable_name: str; body: list[Node] }` — Loop block.
- **Template**: `{ nodes: list[Node] }` — Root container.

## 4. Filter Pipeline Design

### 4.1 Filter Registry

A dictionary maps filter names to callables:

| Filter | Function | Effect |
|--------|----------|--------|
| `upper` | `str.upper` | Convert to uppercase |
| `lower` | `str.lower` | Convert to lowercase |
| `capitalize` | `str.capitalize` | Capitalize first letter |

### 4.2 Chaining

For `{{name|upper|capitalize}}`:
1. Resolve `name` from context → `"hello world"`.
2. Apply `upper` → `"HELLO WORLD"`.
3. Apply `capitalize` → `"Hello world"`.

Filters are applied left-to-right. Each filter receives the string output of the previous filter.

### 4.3 Extensibility

The filter registry is a class attribute of `TemplateEngine`. Users can add custom filters via `engine.add_filter(name, callable)`.

## 5. Rendering

### 5.1 Context Resolution

Variable names support dot notation (e.g., `user.name`). Resolution walks the context dictionary:
1. Split name by `.`.
2. Start with `context[parts[0]]`.
3. For each subsequent part, access `obj[part]` (dict) or `getattr(obj, part)`.
4. If resolution fails, return an empty string (or raise, configurable).

### 5.2 Condition Evaluation

Since the `ast` module is forbidden for expression evaluation, conditions are evaluated using a safe, limited approach:

- **Simple truthy check**: `{% if user %}` — Resolve `user` from context, evaluate truthiness.
- **Comparison operators**: `{% if count > 0 %}` — Parse the condition string to extract `left`, `operator`, `right`. Resolve variables, then apply the comparison. Supported operators: `==`, `!=`, `>`, `<`, `>=`, `<=`.
- **Boolean keywords**: `not`, `and`, `or` — Handled via recursive splitting.

The evaluator is a hand-written recursive function that splits on `or`, then `and`, then `not`, then compares.

### 5.3 For Loop Rendering

For `{% for item in items %}...{% endfor %}`:
1. Resolve `items` from context (must be iterable).
2. For each element, create a child context with `item` set to the current element.
3. Render the loop body against the child context.
4. Concatenate all iteration results.

## 6. Error Handling Approach

### 6.1 TemplateSyntaxError

```
class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None):
        self.line = line
        super().__init__(f"TemplateSyntaxError at line {line}: {message}" if line else f"TemplateSyntaxError: {message}")
```

### 6.2 Error Cases

| Error | When Raised |
|-------|------------|
| Unclosed `{% if %}` block | `{% if %}` without matching `{% endif %}` |
| Unclosed `{% for %}` block | `{% for %}` without matching `{% endfor %}` |
| Unexpected `{% endif %}` | `{% endif %}` without a preceding `{% if %}` |
| Unexpected `{% endfor %}` | `{% endfor %}` without a preceding `{% for %}` |
| Unexpected `{% else %}` | `{% else %}` outside an `{% if %}` block |
| Invalid variable syntax | `{{ }}` (empty) or malformed expressions |
| Unknown filter | `{{var\|unknown_filter}}` |

## 7. TemplateEngine Class Interface

- `TemplateEngine()` — Constructor. Initializes the filter registry.
- `render(template: str, context: dict) -> str` — Parse and render a template string.
- `add_filter(name: str, func: Callable[[str], str]) -> None` — Register a custom filter.
- `parse(template: str) -> Template` — Parse a template into an AST (for inspection/caching).

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python 3.10+, standard library only | Only `re`, `typing`, and `dataclasses` from the standard library are used. No external packages. |
| 2 | No jinja2/mako; parse templates with regex | All template parsing uses `re` module patterns. No template library is imported. |
| 3 | No ast module for expression evaluation | Conditions are evaluated by a hand-written recursive parser that splits on boolean operators and performs comparisons. The `ast` module is not imported. |
| 4 | Full type annotations on all public methods | All public methods of `TemplateEngine` and all node dataclasses have complete type annotations. |
| 5 | TemplateSyntaxError for malformed templates | A custom `TemplateSyntaxError(Exception)` is raised for unclosed blocks, unexpected tags, empty variables, and unknown filters. Includes line number when available. |
| 6 | Single Python file with TemplateEngine class | All node types, the parser, renderer, filter registry, and `TemplateEngine` class are in one `.py` file. |
