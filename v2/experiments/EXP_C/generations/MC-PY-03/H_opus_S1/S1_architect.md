# Technical Design Document: Template Engine

**Task**: MC-PY-03  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]PY310 [D]STDLIB_ONLY [!D]NO_TMPL_LIB [PARSE]REGEX [!D]NO_AST [TYPE]FULL_HINTS [ERR]SYNTAX_EXC [O]CLASS [FILE]SINGLE`

---

## 1. Regex Patterns for Each Template Construct

### Variable Substitution

```python
VAR_PATTERN = r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}'
# Matches: {{ var }}, {{ var|upper }}, {{ var|upper|capitalize }}
# Groups: "var", "var|upper", "var|upper|capitalize"
```

### Conditionals

```python
IF_OPEN = r'\{%\s*if\s+(.+?)\s*%\}'
ELSE_TAG = r'\{%\s*else\s*%\}'
ENDIF_TAG = r'\{%\s*endif\s*%\}'
```

### Loops

```python
FOR_OPEN = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}'
# Groups: (loop_var, iterable_name)
ENDFOR_TAG = r'\{%\s*endfor\s*%\}'
```

### Combined Scanner Pattern

A single scanner regex that tokenizes the template into text segments and control tokens:

```python
TOKEN_PATTERN = re.compile(
    r'(\{\{.*?\}\}|\{%.*?%\})',
    re.DOTALL
)
```

This splits the template into alternating text/token segments for sequential parsing.

---

## 2. Parsing Strategy (Stack-Based)

### Tokenization Phase

1. Use `TOKEN_PATTERN.split(template)` to produce a flat list of text and tag tokens.
2. Classify each token:
   - Plain text → `TextNode`
   - `{{ ... }}` → `VarNode`
   - `{% if ... %}` → `IfOpenToken`
   - `{% else %}` → `ElseToken`
   - `{% endif %}` → `IfCloseToken`
   - `{% for ... %}` → `ForOpenToken`
   - `{% endfor %}` → `ForCloseToken`

### AST Construction (Stack-Based)

A stack-based parser builds a tree of nodes:

```
Initialize: stack = [RootNode]

For each token:
  TextNode / VarNode:
    → append to stack[-1].children

  IfOpenToken:
    → create IfNode(condition)
    → append to stack[-1].children
    → push IfNode onto stack

  ElseToken:
    → validate stack[-1] is IfNode
    → switch IfNode to its else_branch

  IfCloseToken:
    → validate stack[-1] is IfNode
    → pop stack

  ForOpenToken:
    → create ForNode(loop_var, iterable)
    → append to stack[-1].children
    → push ForNode onto stack

  ForCloseToken:
    → validate stack[-1] is ForNode
    → pop stack

Final: if stack has more than RootNode → raise SyntaxError (unclosed block)
```

### Node Types

```python
class TextNode:
    text: str

class VarNode:
    var_name: str
    filters: list[str]

class IfNode:
    condition: str
    true_branch: list[Node]
    false_branch: list[Node]

class ForNode:
    loop_var: str
    iterable_name: str
    body: list[Node]

Node = TextNode | VarNode | IfNode | ForNode
```

---

## 3. Filter Pipeline Design

### Built-in Filters

| Filter | Input | Output | Example |
|--------|-------|--------|---------|
| `upper` | `str` | `str.upper()` | `"hello"` → `"HELLO"` |
| `lower` | `str` | `str.lower()` | `"HELLO"` → `"hello"` |
| `capitalize` | `str` | `str.capitalize()` | `"hello world"` → `"Hello world"` |

### Filter Registry

```python
class FilterRegistry:
    _filters: dict[str, Callable[[str], str]]

    def __init__(self) -> None:
        self._filters = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def apply(self, value: str, filter_names: list[str]) -> str:
        result = value
        for name in filter_names:
            if name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {name}")
            result = self._filters[name](result)
        return result
```

### Chained Filters

`{{ name|upper|capitalize }}` is parsed as:
1. Resolve `name` from context → `"hello world"`
2. Apply `upper` → `"HELLO WORLD"`
3. Apply `capitalize` → `"Hello world"`

Filters are applied left-to-right as a pipeline.

---

## 4. Error Handling Approach

### Custom Exception

```python
class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        prefix = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")
```

### Error Detection Points

| Error | When Detected | Message |
|-------|--------------|---------|
| Unclosed `{% if %}` | End of parsing (stack not empty) | `"Unclosed if block"` |
| Unclosed `{% for %}` | End of parsing (stack not empty) | `"Unclosed for block"` |
| Unexpected `{% endif %}` | Pop from stack, top is not IfNode | `"endif without matching if"` |
| Unexpected `{% endfor %}` | Pop from stack, top is not ForNode | `"endfor without matching for"` |
| `{% else %}` outside if | Stack top is not IfNode | `"else without matching if"` |
| Unknown variable | Render time, variable not in context | `"Undefined variable: {name}"` |
| Unknown filter | Filter apply time | `"Unknown filter: {name}"` |
| Malformed tag | Regex doesn't match any known pattern | `"Invalid template tag: {tag}"` |

### Error Strategy

- **Parse-time errors** (syntax): Raised immediately as `TemplateSyntaxError`. The template is not rendered.
- **Render-time errors** (undefined variables): Configurable — strict mode raises, lenient mode substitutes empty string.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Python 3.10+ | `[L]PY310` | Uses `X \| Y` type unions, `match` statement (optional), modern type syntax. |
| Stdlib only | `[D]STDLIB_ONLY` | Only `re`, `typing`, `dataclasses` from stdlib. No external packages. |
| No template library | `[!D]NO_TMPL_LIB` | No Jinja2, Mako, Django templates, or any templating library. Engine built from scratch. |
| Parsing via regex | `[PARSE]REGEX` | All template constructs are matched and tokenized using `re` module regex patterns. |
| No AST module | `[!D]NO_AST` | Python's `ast` module is not used. The template AST is a custom tree of `TextNode`, `VarNode`, `IfNode`, `ForNode`. |
| Full type hints | `[TYPE]FULL_HINTS` | All classes, methods, functions, and variables are fully type-annotated. |
| Syntax error exception | `[ERR]SYNTAX_EXC` | Custom `TemplateSyntaxError` exception raised for all parse-time and render-time errors. |
| Class-based output | `[O]CLASS` | `TemplateEngine`, `FilterRegistry`, `TemplateSyntaxError`, and all node types are classes. |
| Single file | `[FILE]SINGLE` | All classes and logic in one `.py` file. |
