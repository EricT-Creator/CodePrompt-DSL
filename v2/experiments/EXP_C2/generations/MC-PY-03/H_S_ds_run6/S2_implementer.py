import re
from typing import Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

class NodeKind(Enum):
    TEXT_CONTENT = "text"
    VARIABLE_EXPR = "variable"
    CONDITION_BLOCK = "if"
    LOOP_BLOCK = "for"

@dataclass
class TemplateNode:
    kind: NodeKind
    payload: Any
    child_nodes: List['TemplateNode'] = field(default_factory=list)

class TemplateSyntaxException(Exception):
    """Exception for template syntax errors."""
    pass

class RegexTemplateEngine:
    """Regex-based template engine implementing the technical design."""
    
    # Regex patterns from the design document
    VARIABLE_PAT = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_START_PAT = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    IF_END_PAT = re.compile(r'\{%\s*endif\s*%\}')
    FOR_START_PAT = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_END_PAT = re.compile(r'\{%\s*endfor\s*%\}')
    TOKENIZER_PAT = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize with built-in filters."""
        self.filters: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'trim': str.strip,
        }
    
    def tokenize_template(self, source: str) -> List[Dict[str, Any]]:
        """Tokenize template using the master tokenizer regex."""
        tokens = []
        current_pos = 0
        last_match_end = 0
        
        for match in self.TOKENIZER_PAT.finditer(source):
            # Capture literal text before the tag
            if last_match_end < match.start():
                literal = source[last_match_end:match.start()]
                tokens.append({'type': 'text', 'content': literal})
            
            tag = match.group()
            
            # Handle variable tags
            if tag.startswith('{{'):
                var_match = self.VARIABLE_PAT.match(tag)
                if not var_match:
                    raise TemplateSyntaxException(f"Malformed variable: {tag}")
                
                parts = var_match.group(1).split('|')
                var_name = parts[0]
                filter_list = parts[1:] if len(parts) > 1 else []
                
                tokens.append({
                    'type': 'var',
                    'name': var_name,
                    'filters': filter_list,
                    'raw': tag
                })
            
            # Handle if opening tags
            elif tag.startswith('{% if'):
                if_match = self.IF_START_PAT.match(tag)
                if not if_match:
                    raise TemplateSyntaxException(f"Invalid if: {tag}")
                
                tokens.append({
                    'type': 'if_begin',
                    'condition': if_match.group(1),
                    'raw': tag
                })
            
            # Handle if closing tags
            elif tag == '{% endif %}':
                tokens.append({'type': 'if_end', 'raw': tag})
            
            # Handle for opening tags
            elif tag.startswith('{% for'):
                for_match = self.FOR_START_PAT.match(tag)
                if not for_match:
                    raise TemplateSyntaxException(f"Invalid for: {tag}")
                
                tokens.append({
                    'type': 'for_begin',
                    'item': for_match.group(1),
                    'collection': for_match.group(2),
                    'raw': tag
                })
            
            # Handle for closing tags
            elif tag == '{% endfor %}':
                tokens.append({'type': 'for_end', 'raw': tag})
            
            else:
                raise TemplateSyntaxException(f"Unknown template directive: {tag}")
            
            last_match_end = match.end()
        
        # Add remaining literal text
        if last_match_end < len(source):
            tokens.append({'type': 'text', 'content': source[last_match_end:]})
        
        return tokens
    
    def construct_ast(self, tokens: List[Dict[str, Any]]) -> List[TemplateNode]:
        """Build AST with stack-based recursive descent."""
        root_nodes = []
        node_stack = []
        
        for token in tokens:
            if token['type'] == 'text':
                node = TemplateNode(NodeKind.TEXT_CONTENT, token['content'])
                if node_stack:
                    node_stack[-1]['node'].child_nodes.append(node)
                else:
                    root_nodes.append(node)
            
            elif token['type'] == 'var':
                var_node = TemplateNode(
                    NodeKind.VARIABLE_EXPR,
                    {'variable': token['name'], 'filter_chain': token['filters']}
                )
                if node_stack:
                    node_stack[-1]['node'].child_nodes.append(var_node)
                else:
                    root_nodes.append(var_node)
            
            elif token['type'] == 'if_begin':
                if_node = TemplateNode(NodeKind.CONDITION_BLOCK, {'expr': token['condition']})
                if node_stack:
                    node_stack[-1]['node'].child_nodes.append(if_node)
                else:
                    root_nodes.append(if_node)
                node_stack.append({'type': 'if', 'node': if_node})
            
            elif token['type'] == 'if_end':
                if not node_stack or node_stack[-1]['type'] != 'if':
                    raise TemplateSyntaxException("Unexpected endif")
                node_stack.pop()
            
            elif token['type'] == 'for_begin':
                for_node = TemplateNode(
                    NodeKind.LOOP_BLOCK,
                    {'loop_var': token['item'], 'iterable': token['collection']}
                )
                if node_stack:
                    node_stack[-1]['node'].child_nodes.append(for_node)
                else:
                    root_nodes.append(for_node)
                node_stack.append({'type': 'for', 'node': for_node})
            
            elif token['type'] == 'for_end':
                if not node_stack or node_stack[-1]['type'] != 'for':
                    raise TemplateSyntaxException("Unexpected endfor")
                node_stack.pop()
        
        if node_stack:
            raise TemplateSyntaxException(f"Unclosed {node_stack[-1]['type']} block")
        
        return root_nodes
    
    def evaluate_condition(self, expression: str, data: Dict[str, Any]) -> bool:
        """Evaluate if condition with truthy checks and basic comparisons."""
        expr = expression.strip()
        
        # Direct variable check
        if expr in data:
            value = data[expr]
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
        if '==' in expr:
            left, right = expr.split('==', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(data.get(left, '')) == right
        
        # Inequality comparison
        if '!=' in expr:
            left, right = expr.split('!=', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(data.get(left, '')) != right
        
        return False
    
    def process_node(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        """Process a single AST node."""
        if node.kind == NodeKind.TEXT_CONTENT:
            return node.payload
        
        elif node.kind == NodeKind.VARIABLE_EXPR:
            var_info = node.payload
            value = context.get(var_info['variable'], '')
            
            if value is None:
                value = ''
            else:
                value = str(value)
            
            for filter_name in var_info['filter_chain']:
                if filter_name in self.filters:
                    value = self.filters[filter_name](value)
                else:
                    raise TemplateSyntaxException(f"Unknown filter: {filter_name}")
            
            return value
        
        elif node.kind == NodeKind.CONDITION_BLOCK:
            condition = node.payload['expr']
            if self.evaluate_condition(condition, context):
                return ''.join(self.process_node(child, context) for child in node.child_nodes)
            return ''
        
        elif node.kind == NodeKind.LOOP_BLOCK:
            loop_info = node.payload
            loop_var = loop_info['loop_var']
            iterable_name = loop_info['iterable']
            
            items = context.get(iterable_name, [])
            if not isinstance(items, (list, tuple)):
                items = []
            
            result_parts = []
            for item in items:
                new_context = context.copy()
                new_context[loop_var] = item
                result_parts.append(
                    ''.join(self.process_node(child, new_context) for child in node.child_nodes)
                )
            
            return ''.join(result_parts)
        
        return ''
    
    def compile(self, template: str) -> List[TemplateNode]:
        """Compile template to AST."""
        tokens = self.tokenize_template(template)
        return self.construct_ast(tokens)
    
    def render(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with data context."""
        ast = self.compile(template)
        return ''.join(self.process_node(node, data) for node in ast)
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter."""
        self.filters[name] = func

def example_usage() -> None:
    """Example demonstrating the template engine."""
    engine = RegexTemplateEngine()
    
    template_example = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{{app_name|title}} - Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background: #f0f0f0; padding: 15px; border-radius: 5px; }
            .card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .highlight { background: #fffacd; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{app_name|upper}} Dashboard</h1>
            <p>Welcome, {{user.name|title}}!</p>
        </div>
        
        <div class="content">
            <h2>Statistics</h2>
            <p>Total Users: {{stats.total_users}}</p>
            <p>Active Sessions: {{stats.active_sessions}}</p>
            
            {% if stats.new_signups > 0 %}
            <div class="card highlight">
                <h3>New Signups Today: {{stats.new_signups}}</h3>
            </div>
            {% endif %}
            
            <h2>Recent Activity</h2>
            <div class="activity-list">
            {% for activity in recent_activity %}
                <div class="card">
                    <h4>{{activity.type|capitalize}}</h4>
                    <p>{{activity.description}}</p>
                    <small>{{activity.timestamp}}</small>
                    {% if activity.important %}
                    <span class="badge">IMPORTANT</span>
                    {% endif %}
                </div>
            {% endfor %}
            </div>
            
            <h2>System Status</h2>
            <ul>
            {% for service in services %}
                <li>
                    {{service.name|title}}: 
                    {% if service.status == 'online' %}
                    <span style="color: green;">● {{service.status|upper}}</span>
                    {% else %}
                    <span style="color: red;">● {{service.status|upper}}</span>
                    {% endif %}
                </li>
            {% endfor %}
            </ul>
        </div>
        
        <footer>
            <p>Generated on {{generated_date}}</p>
            <p>Environment: {{environment|upper}}</p>
        </footer>
    </body>
    </html>
    """
    
    data_context = {
        'app_name': 'monitoring system',
        'user': {'name': 'alex johnson', 'role': 'admin'},
        'stats': {
            'total_users': 1542,
            'active_sessions': 87,
            'new_signups': 12
        },
        'recent_activity': [
            {'type': 'login', 'description': 'User "bob123" logged in', 'timestamp': '10:30 AM', 'important': False},
            {'type': 'error', 'description': 'Database connection timeout', 'timestamp': '10:15 AM', 'important': True},
            {'type': 'update', 'description': 'System configuration updated', 'timestamp': '09:45 AM', 'important': True},
            {'type': 'backup', 'description': 'Nightly backup completed', 'timestamp': '03:00 AM', 'important': False},
        ],
        'services': [
            {'name': 'web server', 'status': 'online'},
            {'name': 'database', 'status': 'online'},
            {'name': 'cache', 'status': 'online'},
            {'name': 'email service', 'status': 'offline'},
            {'name': 'file storage', 'status': 'online'},
        ],
        'generated_date': '2024-03-15 10:45:00',
        'environment': 'production'
    }
    
    try:
        result = engine.render(template_example, data_context)
        print(result)
    except TemplateSyntaxException as e:
        print(f"Template error: {e}")

if __name__ == "__main__":
    example_usage()