import re
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

class TemplateNodeKind(Enum):
    TEXT = "text"
    VAR = "variable"
    IF = "if"
    FOR = "for"

@dataclass
class TemplateNode:
    kind: TemplateNodeKind
    data: Any
    children: List['TemplateNode'] = field(default_factory=list)

class TemplateError(Exception):
    """Base exception for template errors."""
    pass

class RegexTemplateEngine:
    """Regex-based template engine implementing the technical design."""
    
    # Regex patterns from the design
    VAR_REGEX = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_OPEN_REGEX = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    IF_CLOSE_REGEX = re.compile(r'\{%\s*endif\s*%\}')
    FOR_OPEN_REGEX = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_CLOSE_REGEX = re.compile(r'\{%\s*endfor\s*%\}')
    TOKENIZER_REGEX = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize with default filters."""
        self.filter_functions: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
        }
    
    def tokenize(self, template: str) -> List[Dict]:
        """Tokenize template into literal text and control tokens."""
        tokens = []
        position = 0
        last_end = 0
        
        for match in self.TOKENIZER_REGEX.finditer(template):
            # Add literal text before the match
            if last_end < match.start():
                literal = template[last_end:match.start()]
                tokens.append({'type': 'literal', 'value': literal})
            
            tag = match.group()
            
            # Handle variable tags
            if tag.startswith('{{'):
                var_match = self.VAR_REGEX.match(tag)
                if not var_match:
                    raise TemplateError(f"Invalid variable syntax: {tag}")
                
                parts = var_match.group(1).split('|')
                var_name = parts[0]
                filters = parts[1:] if len(parts) > 1 else []
                
                tokens.append({
                    'type': 'variable',
                    'name': var_name,
                    'filters': filters,
                    'raw': tag
                })
            
            # Handle if opening tags
            elif tag.startswith('{% if'):
                if_match = self.IF_OPEN_REGEX.match(tag)
                if not if_match:
                    raise TemplateError(f"Invalid if syntax: {tag}")
                
                tokens.append({
                    'type': 'if_open',
                    'condition': if_match.group(1),
                    'raw': tag
                })
            
            # Handle if closing tags
            elif tag == '{% endif %}':
                tokens.append({'type': 'if_close', 'raw': tag})
            
            # Handle for opening tags
            elif tag.startswith('{% for'):
                for_match = self.FOR_OPEN_REGEX.match(tag)
                if not for_match:
                    raise TemplateError(f"Invalid for syntax: {tag}")
                
                tokens.append({
                    'type': 'for_open',
                    'var_name': for_match.group(1),
                    'iterable_name': for_match.group(2),
                    'raw': tag
                })
            
            # Handle for closing tags
            elif tag == '{% endfor %}':
                tokens.append({'type': 'for_close', 'raw': tag})
            
            else:
                raise TemplateError(f"Unknown template construct: {tag}")
            
            last_end = match.end()
        
        # Add remaining literal text
        if last_end < len(template):
            tokens.append({'type': 'literal', 'value': template[last_end:]})
        
        return tokens
    
    def parse(self, tokens: List[Dict]) -> List[TemplateNode]:
        """Parse tokens into AST with stack-based recursive descent."""
        root_nodes = []
        stack = []
        
        for token in tokens:
            if token['type'] == 'literal':
                node = TemplateNode(TemplateNodeKind.TEXT, token['value'])
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
            
            elif token['type'] == 'variable':
                node = TemplateNode(
                    TemplateNodeKind.VAR,
                    {'name': token['name'], 'filters': token['filters']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
            
            elif token['type'] == 'if_open':
                node = TemplateNode(TemplateNodeKind.IF, {'condition': token['condition']})
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
                stack.append({'type': 'if', 'node': node})
            
            elif token['type'] == 'if_close':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateError("Unexpected endif")
                stack.pop()
            
            elif token['type'] == 'for_open':
                node = TemplateNode(
                    TemplateNodeKind.FOR,
                    {'var_name': token['var_name'], 'iterable_name': token['iterable_name']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
                stack.append({'type': 'for', 'node': node})
            
            elif token['type'] == 'for_close':
                if not stack or stack[-1]['type'] != 'for':
                    raise TemplateError("Unexpected endfor")
                stack.pop()
        
        if stack:
            raise TemplateError(f"Unclosed block: {stack[-1]['type']}")
        
        return root_nodes
    
    def evaluate_if_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate if condition using simple truthy checks and basic comparisons."""
        condition = condition.strip()
        
        # Direct variable truthy check
        if condition in context:
            value = context[condition]
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                return bool(value.strip())
            if isinstance(value, (list, dict)):
                return bool(value)
            return bool(value)
        
        # Equality comparison
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) == right
        
        # Inequality comparison
        if '!=' in condition:
            left, right = condition.split('!=', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) != right
        
        return False
    
    def render_node(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        """Render a single AST node to string."""
        if node.kind == TemplateNodeKind.TEXT:
            return node.data
        
        elif node.kind == TemplateNodeKind.VAR:
            var_info = node.data
            value = context.get(var_info['name'], '')
            
            # Convert to string
            if value is None:
                value = ''
            else:
                value = str(value)
            
            # Apply filters in order
            for filter_name in var_info['filters']:
                if filter_name in self.filter_functions:
                    value = self.filter_functions[filter_name](value)
                else:
                    raise TemplateError(f"Unknown filter: {filter_name}")
            
            return value
        
        elif node.kind == TemplateNodeKind.IF:
            condition = node.data['condition']
            if self.evaluate_if_condition(condition, context):
                return ''.join(self.render_node(child, context) for child in node.children)
            return ''
        
        elif node.kind == TemplateNodeKind.FOR:
            loop_info = node.data
            var_name = loop_info['var_name']
            iterable_name = loop_info['iterable_name']
            
            iterable = context.get(iterable_name, [])
            if not isinstance(iterable, (list, tuple)):
                iterable = []
            
            result_parts = []
            for item in iterable:
                new_context = context.copy()
                new_context[var_name] = item
                result_parts.append(
                    ''.join(self.render_node(child, new_context) for child in node.children)
                )
            
            return ''.join(result_parts)
        
        return ''
    
    def compile_template(self, template: str) -> List[TemplateNode]:
        """Compile template string to AST."""
        tokens = self.tokenize(template)
        return self.parse(tokens)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with given context."""
        ast = self.compile_template(template)
        return ''.join(self.render_node(node, context) for node in ast)
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter function."""
        self.filter_functions[name] = func

def test_engine() -> None:
    """Test the template engine with an example."""
    engine = RegexTemplateEngine()
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{page_title|capitalize}}</title>
    </head>
    <body>
        <h1>Welcome, {{user_name|title}}</h1>
        
        {% if is_admin %}
        <div class="admin-panel">
            <p>Administrator Controls</p>
        </div>
        {% endif %}
        
        <h2>Recent Activities:</h2>
        <ul>
        {% for activity in activities %}
            <li>{{activity.name|upper}} at {{activity.time}}</li>
        {% endfor %}
        </ul>
        
        {% if has_messages %}
        <p>You have {{message_count}} new messages.</p>
        {% endif %}
    </body>
    </html>
    """
    
    context = {
        'page_title': 'user dashboard',
        'user_name': 'john doe',
        'is_admin': True,
        'activities': [
            {'name': 'login', 'time': '10:30'},
            {'name': 'file upload', 'time': '11:15'},
            {'name': 'comment post', 'time': '12:45'},
        ],
        'has_messages': True,
        'message_count': 3
    }
    
    try:
        output = engine.render(template, context)
        print(output)
    except TemplateError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_engine()