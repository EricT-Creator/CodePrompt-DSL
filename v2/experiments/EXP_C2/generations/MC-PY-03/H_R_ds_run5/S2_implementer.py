import re
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

class NodeType(Enum):
    TEXT = "text"
    VARIABLE = "variable"
    IF = "if"
    FOR = "for"

@dataclass
class Node:
    node_type: NodeType
    content: Any
    children: List['Node'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class TemplateSyntaxError(Exception):
    """Custom exception for template syntax errors."""
    pass

class RegexTemplateEngine:
    """Regex-based template engine with full Python 3.10+ type hints."""
    
    # Regex patterns
    VARIABLE_PATTERN = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_OPEN_PATTERN = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    IF_CLOSE_PATTERN = re.compile(r'\{%\s*endif\s*%\}')
    FOR_OPEN_PATTERN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_CLOSE_PATTERN = re.compile(r'\{%\s*endfor\s*%\}')
    TOKENIZER_PATTERN = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize the template engine with default filters."""
        self.filters: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'strip': str.strip,
            'lstrip': str.lstrip,
            'rstrip': str.rstrip,
        }
    
    def tokenize(self, template: str) -> List[Dict[str, Any]]:
        """Split template into tokens."""
        tokens: List[Dict[str, Any]] = []
        pos = 0
        last_pos = 0
        
        for match in self.TOKENIZER_PATTERN.finditer(template):
            # Add literal text before match
            if last_pos < match.start():
                literal = template[last_pos:match.start()]
                tokens.append({'type': 'literal', 'content': literal})
            
            # Process the matched token
            token_text = match.group()
            
            # Variable substitution
            if token_text.startswith('{{'):
                var_match = self.VARIABLE_PATTERN.match(token_text)
                if var_match:
                    parts = var_match.group(1).split('|')
                    var_name = parts[0]
                    filter_names = parts[1:] if len(parts) > 1 else []
                    tokens.append({
                        'type': 'variable',
                        'var_name': var_name,
                        'filters': filter_names,
                        'raw': token_text
                    })
                else:
                    raise TemplateSyntaxError(f"Invalid variable syntax: {token_text}")
            
            # If opening
            elif token_text.startswith('{% if'):
                if_match = self.IF_OPEN_PATTERN.match(token_text)
                if if_match:
                    tokens.append({
                        'type': 'if_open',
                        'condition': if_match.group(1),
                        'raw': token_text
                    })
                else:
                    raise TemplateSyntaxError(f"Invalid if syntax: {token_text}")
            
            # If closing
            elif token_text == '{% endif %}':
                tokens.append({'type': 'if_close', 'raw': token_text})
            
            # For opening
            elif token_text.startswith('{% for'):
                for_match = self.FOR_OPEN_PATTERN.match(token_text)
                if for_match:
                    tokens.append({
                        'type': 'for_open',
                        'var_name': for_match.group(1),
                        'iterable_name': for_match.group(2),
                        'raw': token_text
                    })
                else:
                    raise TemplateSyntaxError(f"Invalid for syntax: {token_text}")
            
            # For closing
            elif token_text == '{% endfor %}':
                tokens.append({'type': 'for_close', 'raw': token_text})
            
            else:
                raise TemplateSyntaxError(f"Unknown template tag: {token_text}")
            
            last_pos = match.end()
        
        # Add remaining literal text
        if last_pos < len(template):
            tokens.append({'type': 'literal', 'content': template[last_pos:]})
        
        return tokens
    
    def parse(self, tokens: List[Dict[str, Any]]) -> List[Node]:
        """Parse tokens into an AST."""
        ast_nodes: List[Node] = []
        stack: List[Dict[str, Any]] = []
        
        for token in tokens:
            if token['type'] == 'literal':
                node = Node(NodeType.TEXT, token['content'])
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    ast_nodes.append(node)
            
            elif token['type'] == 'variable':
                node = Node(
                    NodeType.VARIABLE,
                    {'name': token['var_name'], 'filters': token['filters']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    ast_nodes.append(node)
            
            elif token['type'] == 'if_open':
                node = Node(NodeType.IF, {'condition': token['condition']})
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    ast_nodes.append(node)
                stack.append({'type': 'if', 'node': node})
            
            elif token['type'] == 'if_close':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateSyntaxError("Unexpected endif")
                stack.pop()
            
            elif token['type'] == 'for_open':
                node = Node(
                    NodeType.FOR,
                    {'var_name': token['var_name'], 'iterable_name': token['iterable_name']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    ast_nodes.append(node)
                stack.append({'type': 'for', 'node': node})
            
            elif token['type'] == 'for_close':
                if not stack or stack[-1]['type'] != 'for':
                    raise TemplateSyntaxError("Unexpected endfor")
                stack.pop()
        
        if stack:
            raise TemplateSyntaxError(f"Unclosed block: {stack[-1]['type']}")
        
        return ast_nodes
    
    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate an if condition against context."""
        condition = condition.strip()
        
        # Simple truthy check
        if condition in context:
            value = context[condition]
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                return bool(value.strip())
            if isinstance(value, (list, dict, set)):
                return bool(value)
            return bool(value)
        
        # Basic comparisons
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) == right
        
        if '!=' in condition:
            left, right = condition.split('!=', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) != right
        
        return bool(context.get(condition, False))
    
    def render_node(self, node: Node, context: Dict[str, Any]) -> str:
        """Render a single node to string."""
        if node.node_type == NodeType.TEXT:
            return node.content
        
        elif node.node_type == NodeType.VARIABLE:
            var_info = node.content
            value = context.get(var_info['name'], '')
            
            # Convert to string
            if value is None:
                value = ''
            else:
                value = str(value)
            
            # Apply filters
            for filter_name in var_info['filters']:
                if filter_name in self.filters:
                    value = self.filters[filter_name](value)
                else:
                    raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            
            return value
        
        elif node.node_type == NodeType.IF:
            condition = node.content['condition']
            if self.evaluate_condition(condition, context):
                return ''.join(self.render_node(child, context) for child in node.children)
            return ''
        
        elif node.node_type == NodeType.FOR:
            var_info = node.content
            var_name = var_info['var_name']
            iterable_name = var_info['iterable_name']
            
            iterable = context.get(iterable_name, [])
            if not isinstance(iterable, (list, tuple)):
                iterable = []
            
            result = []
            for item in iterable:
                new_context = context.copy()
                new_context[var_name] = item
                result.append(''.join(self.render_node(child, new_context) for child in node.children))
            
            return ''.join(result)
        
        return ''
    
    def compile(self, template: str) -> List[Node]:
        """Compile template string to AST."""
        tokens = self.tokenize(template)
        return self.parse(tokens)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context."""
        ast_nodes = self.compile(template)
        return ''.join(self.render_node(node, context) for node in ast_nodes)
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Add a custom filter."""
        self.filters[name] = func

def main() -> None:
    """Example usage."""
    engine = RegexTemplateEngine()
    
    # Example template
    template = """
    <h1>Hello {{name|capitalize}}</h1>
    {% if show_details %}
    <p>Details: {{description}}</p>
    {% endif %}
    <ul>
    {% for item in items %}
        <li>{{item|upper}}</li>
    {% endfor %}
    </ul>
    """
    
    # Example context
    context = {
        'name': 'john doe',
        'show_details': True,
        'description': 'This is a test',
        'items': ['apple', 'banana', 'cherry']
    }
    
    try:
        result = engine.render(template, context)
        print(result)
    except TemplateSyntaxError as e:
        print(f"Template error: {e}")

if __name__ == "__main__":
    main()