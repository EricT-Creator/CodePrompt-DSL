# MC-PY-03: Template Engine - Technical Design Document

## 1. Regex Patterns for Template Constructs

### Variable Substitution Pattern
```regex
\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}
```
- Matches: `{{variable}}`, `{{  variable  }}`
- Captures: variable name
- Handles whitespace around variable name

### Filter Pipe Pattern
```regex
\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\|\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}
```
- Matches: `{{var|filter}}`, `{{ var | upper }}`
- Captures: variable name and filter name

### If Conditional Pattern
```
Opening:  {%\s*if\s+(.+?)\s*%}
Closing:  {%\s*endif\s*%}
```
- Matches: `{%if condition%}`, `{% endif %}`
- Captures: condition expression

### For Loop Pattern
```
Opening:  {%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%}
Closing:  {%\s*endfor\s*%}
```
- Matches: `{%for item in list%}`, `{% endfor %}`
- Captures: loop variable and iterable name

### Combined Tokenization Pattern
```regex
(\{\{.*?\}\})|(\{%.*?%\})
```
- Identifies all template tokens in single pass
- Separates variables/filters from control structures

## 2. Parsing Strategy

### Stack-Based Parser Architecture

**Token Types:**
```python
from typing import Literal

TokenType = Literal['TEXT', 'VAR', 'VAR_FILTER', 'IF_START', 'IF_END', 'FOR_START', 'FOR_END']

class Token:
    type: TokenType
    content: str
    raw: str
    line: int
```

**Parse Tree Node Types:**
```python
from typing import Union

class TextNode:
    content: str

class VarNode:
    name: str
    filter: str | None

class IfNode:
    condition: str
    then_branch: list[ASTNode]
    else_branch: list[ASTNode] | None

class ForNode:
    var_name: str
    iterable: str
    body: list[ASTNode]

ASTNode = Union[TextNode, VarNode, IfNode, ForNode]
```

### Parsing Algorithm

1. **Tokenization Phase:**
   - Scan template string with combined regex
   - Split into tokens (TEXT, template tags)
   - Track line numbers for error reporting

2. **Structure Parsing Phase:**
   - Initialize empty stack for tracking nested structures
   - Initialize output list for root-level nodes
   - Iterate through tokens:
     - TEXT → Create TextNode, append to current context
     - VAR → Create VarNode, append to current context
     - IF_START → Push new IfNode onto stack, set as current context
     - FOR_START → Push new ForNode onto stack, set as current context
     - IF_END/FOR_END → Pop from stack, append completed node to parent context

3. **Validation Phase:**
   - Check for unclosed tags (non-empty stack)
   - Verify proper nesting (if inside for, etc.)
   - Raise TemplateSyntaxError for malformed templates

### Nested Structure Handling

**Stack Operations:**
```python
# Pseudocode for stack-based parsing
stack: list[tuple[ASTNode, list]] = [(root, [])]

for token in tokens:
    current_node, current_children = stack[-1]
    
    if token.type == 'IF_START':
        new_if = IfNode(condition=token.content)
        stack.append((new_if, new_if.then_branch))
    elif token.type == 'FOR_START':
        new_for = ForNode(var_name=..., iterable=...)
        stack.append((new_for, new_for.body))
    elif token.type in ('IF_END', 'FOR_END'):
        completed, _ = stack.pop()
        stack[-1][1].append(completed)
    else:
        current_children.append(create_node(token))
```

## 3. Filter Pipeline Design

### Built-in Filters
```python
FILTERS: dict[str, Callable[[Any], str]] = {
    'upper': lambda x: str(x).upper(),
    'lower': lambda x: str(x).lower(),
    'capitalize': lambda x: str(x).capitalize(),
}
```

### Filter Application Flow
1. Extract filter name from VarNode
2. Lookup filter in FILTERS dictionary
3. Apply filter to resolved variable value
4. Convert result to string for output

### Extensibility Design
- Filters stored in class-level dictionary
- Custom filters can be registered via `register_filter(name, func)`
- Filter chain support: `{{var|upper|reverse}}` (future extension)

## 4. Error Handling Approach

### TemplateSyntaxError Exception
```python
class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int, column: int | None = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}: {message}")
```

### Error Detection Points

1. **Tokenization Errors:**
   - Malformed variable syntax: `{{incomplete`
   - Unknown tag types: `{% unknown %}`

2. **Parsing Errors:**
   - Unclosed tags: `{% if x %}content` (missing endif)
   - Unexpected closing tags: `{% endif %}` without matching if
   - Improper nesting: `{% if x %}{% for y %}{% endif %}{% endfor %}`

3. **Runtime Errors:**
   - Undefined variables: variable not in context
   - Invalid filter names
   - Non-iterable in for loop

### Error Context Reporting
- Track line numbers during tokenization
- Include surrounding template context in error messages
- Point to exact location of syntax error

## 5. Constraint Acknowledgment

### Python 3.10+, stdlib only
**Addressed by:** Only imports from standard library (re, typing). No external template libraries.

### Regex parsing, no jinja2/mako
**Addressed by:** All parsing implemented using `re` module patterns. No Jinja2, Mako, or other template engines as dependencies.

### No ast module
**Addressed by:** Parser uses regex and stack-based approach. No `ast.parse()` or AST manipulation. Template expressions evaluated safely via context dictionary lookup.

### Full type annotations
**Addressed by:** All classes, methods, and functions have complete type hints. Uses `from __future__ import annotations` for forward references.

### TemplateSyntaxError on errors
**Addressed by:** Custom exception class defined. All parsing errors raise TemplateSyntaxError with line number and descriptive message.

### Single file, class output
**Addressed by:** Single `.py` file containing TemplateEngine class and supporting types. `export` via class instantiation pattern.
