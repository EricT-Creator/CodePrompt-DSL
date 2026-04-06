# MC-PY-03: Template Engine — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Regex Patterns for Each Template Construct

### 1.1 Variable Substitution

```python
import re

# {{ variable }} or {{ variable | filter }}
VARIABLE_PATTERN = re.compile(
    r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\|\s*([a-zA-Z_][a-zA-Z0-9_]*))?\s*\}\}'
)

# Matches:
# {{ name }}
# {{ name|upper }}
# {{   name   |   upper   }}
```

### 1.2 Conditionals

```python
# {% if condition %} ... {% endif %}
IF_PATTERN = re.compile(
    r'{%\s*if\s+(.+?)\s*%}(.*?){%\s*endif\s*%}',
    re.DOTALL
)

# Matches:
# {% if user %}Hello{% endif %}
```

### 1.3 For Loops

```python
# {% for item in list %} ... {% endfor %}
FOR_PATTERN = re.compile(
    r'{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%}'
    r'(.*?)'
    r'{%\s*endfor\s*%}',
    re.DOTALL
)

# Matches:
# {% for item in items %}{{ item }}{% endfor %}
```

### 1.4 Pattern Summary

| Construct | Pattern |
|-----------|---------|
| Variable | `\{\{\s*(\w+)\s*(?:\|\s*(\w+))?\s*\}\}` |
| If | `{%\s*if\s+(.+?)\s*%}(.*?){%\s*endif\s*%}` |
| For | `{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}` |

---

## 2. Parsing Strategy

### 2.1 Recursive/Stack-Based Approach

```python
from typing import Any, Callable
from dataclasses import dataclass

@dataclass
class TemplateNode:
    """Base class for template AST nodes"""
    pass

@dataclass
class TextNode(TemplateNode):
    text: str

@dataclass
class VariableNode(TemplateNode):
    name: str
    filter: str | None

@dataclass
class IfNode(TemplateNode):
    condition: str
    body: list[TemplateNode]

@dataclass
class ForNode(TemplateNode):
    var_name: str
    list_name: str
    body: list[TemplateNode]
```

### 2.2 Parser Implementation

```python
class TemplateParser:
    def __init__(self, template: str):
        self.template = template
        self.pos = 0
    
    def parse(self) -> list[TemplateNode]:
        """Parse template into AST nodes"""
        nodes = []
        while self.pos < len(self.template):
            if self.peek(2) == '{{':
                nodes.append(self.parse_variable())
            elif self.peek(2) == '{%':
                nodes.append(self.parse_tag())
            else:
                nodes.append(self.parse_text())
        return nodes
    
    def parse_variable(self) -> VariableNode:
        """Parse {{ var | filter }}"""
        match = VARIABLE_PATTERN.match(self.template, self.pos)
        if not match:
            raise TemplateSyntaxError("Invalid variable syntax")
        
        self.pos = match.end()
        return VariableNode(name=match.group(1), filter=match.group(2))
    
    def parse_tag(self) -> TemplateNode:
        """Parse {% ... %} tags"""
        if self.template[self.pos:self.pos+9] == '{% if ':
            return self.parse_if()
        elif self.template[self.pos:self.pos+10] == '{% for ':
            return self.parse_for()
        else:
            raise TemplateSyntaxError("Unknown tag")
```

### 2.3 Stack-Based Nesting

```python
def parse_if(self) -> IfNode:
    """Parse if block with nested content"""
    # Find matching endif
    start = self.pos
    depth = 1
    pos = self.pos + 9  # Skip '{% if '
    
    while pos < len(self.template) and depth > 0:
        if self.template[pos:pos+9] == '{% if ':
            depth += 1
            pos += 9
        elif self.template[pos:pos+12] == '{% endif %':
            depth -= 1
            if depth == 0:
                break
            pos += 12
        else:
            pos += 1
    
    if depth > 0:
        raise TemplateSyntaxError("Unclosed if block")
    
    # Extract condition and body
    match = IF_PATTERN.match(self.template[start:pos+12])
    condition = match.group(1)
    body_text = match.group(2)
    
    # Recursively parse body
    body_parser = TemplateParser(body_text)
    body = body_parser.parse()
    
    self.pos = pos + 12
    return IfNode(condition=condition, body=body)
```

---

## 3. Filter Pipeline Design

### 3.1 Built-in Filters

```python
FILTERS: dict[str, Callable[[Any], str]] = {
    'upper': lambda x: str(x).upper(),
    'lower': lambda x: str(x).lower(),
    'capitalize': lambda x: str(x).capitalize(),
    'trim': lambda x: str(x).strip(),
}

def apply_filter(value: Any, filter_name: str) -> str:
    """Apply named filter to value"""
    if filter_name not in FILTERS:
        raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
    return FILTERS[filter_name](value)
```

### 3.2 Chained Filters (Future)

```python
# {{ name|trim|upper }}
def apply_filters(value: Any, filter_chain: list[str]) -> str:
    result = value
    for f in filter_chain:
        result = apply_filter(result, f)
    return result
```

---

## 4. Error Handling Approach

### 4.1 SyntaxError Definition

```python
class TemplateSyntaxError(Exception):
    """Raised for template syntax errors"""
    def __init__(self, message: str, line: int = None, col: int = None):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(self._format())
    
    def _format(self) -> str:
        loc = f" at line {self.line}, col {self.col}" if self.line else ""
        return f"Template syntax error{loc}: {self.message}"
```

### 4.2 Runtime Errors

```python
class TemplateRuntimeError(Exception):
    """Raised during template rendering"""
    pass

def render_variable(name: str, context: dict) -> str:
    """Safely get variable from context"""
    if name not in context:
        raise TemplateRuntimeError(f"Variable '{name}' not defined")
    return str(context[name])
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]PY310` | Python 3.10+ features |
| `[D]STDLIB_ONLY` | Only re module from stdlib |
| `[!D]NO_TMPL_LIB` | No jinja2 or similar |
| `[PARSE]REGEX` | Regex-based parsing |
| `[!D]NO_AST` | No ast module; custom parser |
| `[TYPE]FULL_HINTS` | Full type annotations |
| `[ERR]SYNTAX_EXC` | TemplateSyntaxError for errors |
| `[O]CLASS` | TemplateEngine as class |
| `[FILE]SINGLE` | Single file implementation |

---

## 6. TemplateEngine Class

```python
@dataclass
class TemplateEngine:
    template: str
    _ast: list[TemplateNode] = field(init=False)
    
    def __post_init__(self):
        parser = TemplateParser(self.template)
        self._ast = parser.parse()
    
    def render(self, context: dict[str, Any]) -> str:
        """Render template with given context"""
        return self._render_nodes(self._ast, context)
    
    def _render_nodes(self, nodes: list[TemplateNode], context: dict) -> str:
        """Recursively render AST nodes"""
        result = []
        for node in nodes:
            if isinstance(node, TextNode):
                result.append(node.text)
            elif isinstance(node, VariableNode):
                value = render_variable(node.name, context)
                if node.filter:
                    value = apply_filter(value, node.filter)
                result.append(value)
            elif isinstance(node, IfNode):
                if self._eval_condition(node.condition, context):
                    result.append(self._render_nodes(node.body, context))
            elif isinstance(node, ForNode):
                list_value = context.get(node.list_name, [])
                for item in list_value:
                    ctx = {**context, node.var_name: item}
                    result.append(self._render_nodes(node.body, ctx))
        return ''.join(result)
```

---

## 7. File Structure

```
MC-PY-03/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── template_engine.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
