# MC-PY-03: Template Engine - Technical Design

## Overview

This document outlines the technical design for a template engine supporting variable substitution, conditionals, loops, and filter pipes using regex-based parsing.

## 1. Regex Patterns for Template Constructs

### Pattern Definitions

```python
import re
from typing import Pattern

class TemplatePatterns:
    """Regex patterns for template syntax parsing."""
    
    # Variable: {{ variable }} or {{ variable|filter }}
    VARIABLE = re.compile(r'\{\{\s*(\w+)(?:\|(\w+))?\s*\}\}')
    
    # If block: {% if condition %}...{% endif %}
    IF_START = re.compile(r'\{%\s*if\s+(\w+)\s*%\}')
    IF_END = re.compile(r'\{%\s*endif\s*%\}')
    
    # For block: {% for item in list %}...{% endfor %}
    FOR_START = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_END = re.compile(r'\{%\s*endfor\s*%\}')
    
    # Combined block start pattern (for initial tokenization)
    BLOCK_START = re.compile(r'\{%\s*(if|for)\s+')
    BLOCK_END = re.compile(r'\{%\s*end(if|for)\s*%\}')
```

### Pattern Explanations

| Pattern | Regex | Matches |
|---------|-------|---------|
| VARIABLE | `\{\{\s*(\w+)(?:\|(\w+))?\s*\}\}` | `{{name}}`, `{{ name\|upper }}` |
| IF_START | `\{%\s*if\s+(\w+)\s*%\}` | `{% if user %}` |
| IF_END | `\{%\s*endif\s*%\}` | `{% endif %}` |
| FOR_START | `\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}` | `{% for item in items %}` |
| FOR_END | `\{%\s*endfor\s*%\}` | `{% endfor %}` |

## 2. Parsing Strategy

### Token-Based Parsing

```python
from typing import List, Union, Optional
from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    TEXT = auto()
    VARIABLE = auto()
    IF_START = auto()
    IF_END = auto()
    FOR_START = auto()
    FOR_END = auto()

@dataclass
class Token:
    type: TokenType
    content: str
    var_name: Optional[str] = None
    filter_name: Optional[str] = None
    loop_var: Optional[str] = None
    loop_iterable: Optional[str] = None
```

### Tokenizer Implementation

```python
def tokenize(self, template: str) -> List[Token]:
    """
    Tokenize template string into structured tokens.
    
    Uses regex to find template tags and split text into tokens.
    """
    tokens = []
    pos = 0
    
    # Pattern to match any template construct
    pattern = re.compile(r'(\{\{[^}]+\}\}|\{%[^%]+%\})')
    
    for match in pattern.finditer(template):
        # Add text before tag
        if match.start() > pos:
            tokens.append(Token(TokenType.TEXT, template[pos:match.start()]))
        
        tag = match.group(1)
        
        # Parse variable
        var_match = TemplatePatterns.VARIABLE.match(tag)
        if var_match:
            tokens.append(Token(
                TokenType.VARIABLE,
                tag,
                var_name=var_match.group(1),
                filter_name=var_match.group(2)
            ))
            continue
        
        # Parse if start
        if_match = TemplatePatterns.IF_START.match(tag)
        if if_match:
            tokens.append(Token(
                TokenType.IF_START,
                tag,
                var_name=if_match.group(1)
            ))
            continue
        
        # Parse if end
        if TemplatePatterns.IF_END.match(tag):
            tokens.append(Token(TokenType.IF_END, tag))
            continue
        
        # Parse for start
        for_match = TemplatePatterns.FOR_START.match(tag)
        if for_match:
            tokens.append(Token(
                TokenType.FOR_START,
                tag,
                loop_var=for_match.group(1),
                loop_iterable=for_match.group(2)
            ))
            continue
        
        # Parse for end
        if TemplatePatterns.FOR_END.match(tag):
            tokens.append(Token(TokenType.FOR_END, tag))
            continue
        
        pos = match.end()
    
    # Add remaining text
    if pos < len(template):
        tokens.append(Token(TokenType.TEXT, template[pos:]))
    
    return tokens
```

### AST Construction (Stack-Based)

```python
@dataclass
class ASTNode:
    """Base class for AST nodes."""
    pass

@dataclass
class TextNode(ASTNode):
    content: str

@dataclass
class VariableNode(ASTNode):
    name: str
    filter: Optional[str]

@dataclass
class IfNode(ASTNode):
    condition: str
    body: List[ASTNode]

@dataclass
class ForNode(ASTNode):
    var: str
    iterable: str
    body: List[ASTNode]
```

```python
def parse(self, tokens: List[Token]) -> List[ASTNode]:
    """
    Parse tokens into AST using stack-based approach.
    
    Handles nested structures by tracking open blocks on a stack.
    """
    ast_nodes: List[ASTNode] = []
    stack: List[Union[IfNode, ForNode]] = []
    current_body = ast_nodes
    
    for token in tokens:
        if token.type == TokenType.TEXT:
            current_body.append(TextNode(token.content))
        
        elif token.type == TokenType.VARIABLE:
            current_body.append(VariableNode(token.var_name, token.filter_name))
        
        elif token.type == TokenType.IF_START:
            if_node = IfNode(token.var_name, [])
            current_body.append(if_node)
            stack.append(if_node)
            current_body = if_node.body
        
        elif token.type == TokenType.FOR_START:
            for_node = ForNode(token.loop_var, token.loop_iterable, [])
            current_body.append(for_node)
            stack.append(for_node)
            current_body = for_node.body
        
        elif token.type in (TokenType.IF_END, TokenType.FOR_END):
            if not stack:
                raise TemplateSyntaxError(f"Unexpected {token.type.name}")
            
            # Pop from stack
            stack.pop()
            
            # Restore current_body
            if stack:
                current_body = stack[-1].body
            else:
                current_body = ast_nodes
    
    if stack:
        raise TemplateSyntaxError("Unclosed block")
    
    return ast_nodes
```

## 3. Filter Pipeline Design

### Built-in Filters

```python
class FilterRegistry:
    """Registry of available template filters."""
    
    def __init__(self):
        self._filters: Dict[str, Callable[[Any], str]] = {
            'upper': lambda x: str(x).upper(),
            'lower': lambda x: str(x).lower(),
            'capitalize': lambda x: str(x).capitalize(),
        }
    
    def register(self, name: str, func: Callable[[Any], str]) -> None:
        """Register a custom filter."""
        self._filters[name] = func
    
    def apply(self, name: str, value: Any) -> str:
        """Apply a filter to a value."""
        if name not in self._filters:
            raise TemplateSyntaxError(f"Unknown filter: '{name}'")
        return self._filters[name](value)
```

### Filter Chain Support

```python
# Extended pattern for chained filters: {{ var|filter1|filter2 }}
VARIABLE_CHAIN = re.compile(r'\{\{\s*(\w+)\s*((?:\|\s*\w+\s*)*)\}\}')

def parse_filters(self, filter_string: str) -> List[str]:
    """Parse filter chain into list of filter names."""
    return [f.strip() for f in filter_string.split('|') if f.strip()]

def apply_filter_chain(self, value: Any, filters: List[str]) -> str:
    """Apply a chain of filters to a value."""
    result = value
    for filter_name in filters:
        result = self.filters.apply(filter_name, result)
    return result
```

## 4. Error Handling Approach

### TemplateSyntaxError

```python
class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        super().__init__(message)
        self.line = line
        self.column = column
        self.message = message
    
    def __str__(self) -> str:
        if self.line:
            return f"Template syntax error at line {self.line}: {self.message}"
        return f"Template syntax error: {self.message}"
```

### Error Detection Points

```python
def validate_syntax(self, template: str) -> None:
    """
    Validate template syntax before rendering.
    
    Checks:
    - Balanced block tags (if/endif, for/endfor)
    - Valid variable names
    - Known filters
    - Proper nesting
    """
    # Check for unclosed tags
    if_count = len(re.findall(TemplatePatterns.IF_START, template))
    endif_count = len(re.findall(TemplatePatterns.IF_END, template))
    if if_count != endif_count:
        raise TemplateSyntaxError(
            f"Unmatched if tags: {if_count} if, {endif_count} endif"
        )
    
    for_count = len(re.findall(TemplatePatterns.FOR_START, template))
    endfor_count = len(re.findall(TemplatePatterns.FOR_END, template))
    if for_count != endfor_count:
        raise TemplateSyntaxError(
            f"Unmatched for tags: {for_count} for, {endfor_count} endfor"
        )
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python 3.10+, standard library only** | No external dependencies; use re, typing, dataclasses |
| **Regex for parsing** | Define patterns for {{var}}, {% if %}, {% for %} constructs |
| **No ast module** | Use stack-based parsing for control structures, not Python AST |
| **Full type annotations** | All methods typed with List, Dict, Optional, Callable, Any |
| **Custom TemplateSyntaxError** | Define exception class with line/column info |
| **Single Python file** | TemplateEngine class with all supporting classes |

## Summary

This design implements a template engine using regex-based parsing. The tokenizer identifies template constructs (variables, if blocks, for loops) and converts them to tokens. A stack-based parser builds an AST that handles nested structures. The filter registry supports variable transformation pipelines. TemplateSyntaxError provides clear error messages for malformed templates. The rendering phase walks the AST, evaluating variables from context and executing control flow.
