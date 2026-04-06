import re
from typing import Dict, List, Any, Callable, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

class TemplateNodeType(Enum):
    PLAIN_TEXT = "plain_text"
    VARIABLE = "variable"
    CONDITIONAL = "conditional"
    LOOP = "loop"

@dataclass
class TemplateNode:
    kind: TemplateNodeType
    data: Any
    inner_nodes: List['TemplateNode'] = field(default_factory=list)

class TemplateSyntaxException(Exception):
    """Exception for template syntax errors."""
    pass

class RegexTemplateParser:
    """Regex-based template engine with full Python 3.10+ typing."""
    
    # Pattern definitions
    VAR_PAT = re.compile(r'\{\{\s*([a-zA-Z_]\w*(?:\|[a-zA-Z_]\w*)*)\s*\}\}')
    IF_START_PAT = re.compile(r'\{%\s*if\s+([^%]+?)\s*%\}')
    IF_END_PAT = re.compile(r'\{%\s*endif\s*%\}')
    LOOP_START_PAT = re.compile(r'\{%\s*for\s+([a-zA-Z_]\w+)\s+in\s+([a-zA-Z_]\w+)\s*%\}')
    LOOP_END_PAT = re.compile(r'\{%\s*endfor\s*%\}')
    TOKEN_SPLIT_PAT = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize with built-in filters."""
        self.filter_registry: Dict[str, Callable[[str], str]] = {
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'capitalize': lambda s: s.capitalize(),
            'title': lambda s: s.title(),
            'trim': lambda s: s.strip(),
            'replace_spaces': lambda s: s.replace(' ', '_'),
        }
    
    def tokenize_template(self, source: str) -> List[Dict]:
        """Break template into tokens."""
        tokens = []
        current_pos = 0
        last_match_end = 0
        
        for match in self.TOKEN_SPLIT_PAT.finditer(source):
            # Capture literal text before the tag
            if last_match_end < match.start():
                literal_text = source[last_match_end:match.start()]
                tokens.append({
                    'token_type': 'text',
                    'content': literal_text
                })
            
            tag_content = match.group()
            
            # Variable substitution
            if tag_content.startswith('{{'):
                var_match = self.VAR_PAT.match(tag_content)
                if not var_match:
                    raise TemplateSyntaxException(f"Malformed variable: {tag_content}")
                
                parts = var_match.group(1).split('|')
                variable = parts[0]
                filter_chain = parts[1:] if len(parts) > 1 else []
                
                tokens.append({
                    'token_type': 'var',
                    'variable': variable,
                    'filters': filter_chain,
                    'original': tag_content
                })
            
            # If statement start
            elif tag_content.startswith('{% if'):
                if_start = self.IF_START_PAT.match(tag_content)
                if not if_start:
                    raise TemplateSyntaxException(f"Invalid if statement: {tag_content}")
                
                tokens.append({
                    'token_type': 'if_begin',
                    'condition': if_start.group(1),
                    'original': tag_content
                })
            
            # If statement end
            elif tag_content == '{% endif %}':
                tokens.append({
                    'token_type': 'if_end',
                    'original': tag_content
                })
            
            # Loop start
            elif tag_content.startswith('{% for'):
                loop_match = self.LOOP_START_PAT.match(tag_content)
                if not loop_match:
                    raise TemplateSyntaxException(f"Invalid for loop: {tag_content}")
                
                tokens.append({
                    'token_type': 'loop_begin',
                    'item_var': loop_match.group(1),
                    'collection': loop_match.group(2),
                    'original': tag_content
                })
            
            # Loop end
            elif tag_content == '{% endfor %}':
                tokens.append({
                    'token_type': 'loop_end',
                    'original': tag_content
                })
            
            else:
                raise TemplateSyntaxException(f"Unknown template directive: {tag_content}")
            
            last_match_end = match.end()
        
        # Add remaining literal text
        if last_match_end < len(source):
            tokens.append({
                'token_type': 'text',
                'content': source[last_match_end:]
            })
        
        return tokens
    
    def build_ast(self, tokens: List[Dict]) -> List[TemplateNode]:
        """Construct AST from tokens."""
        root_nodes = []
        node_stack = []
        
        for token in tokens:
            if token['token_type'] == 'text':
                new_node = TemplateNode(TemplateNodeType.PLAIN_TEXT, token['content'])
                if node_stack:
                    node_stack[-1]['node'].inner_nodes.append(new_node)
                else:
                    root_nodes.append(new_node)
            
            elif token['token_type'] == 'var':
                var_node = TemplateNode(
                    TemplateNodeType.VARIABLE,
                    {'name': token['variable'], 'filter_list': token['filters']}
                )
                if node_stack:
                    node_stack[-1]['node'].inner_nodes.append(var_node)
                else:
                    root_nodes.append(var_node)
            
            elif token['token_type'] == 'if_begin':
                if_node = TemplateNode(
                    TemplateNodeType.CONDITIONAL,
                    {'expression': token['condition']}
                )
                if node_stack:
                    node_stack[-1]['node'].inner_nodes.append(if_node)
                else:
                    root_nodes.append(if_node)
                node_stack.append({'type': 'if', 'node': if_node})
            
            elif token['token_type'] == 'if_end':
                if not node_stack or node_stack[-1]['type'] != 'if':
                    raise TemplateSyntaxException("Unexpected endif without matching if")
                node_stack.pop()
            
            elif token['token_type'] == 'loop_begin':
                loop_node = TemplateNode(
                    TemplateNodeType.LOOP,
                    {
                        'item_name': token['item_var'],
                        'list_name': token['collection']
                    }
                )
                if node_stack:
                    node_stack[-1]['node'].inner_nodes.append(loop_node)
                else:
                    root_nodes.append(loop_node)
                node_stack.append({'type': 'loop', 'node': loop_node})
            
            elif token['token_type'] == 'loop_end':
                if not node_stack or node_stack[-1]['type'] != 'loop':
                    raise TemplateSyntaxException("Unexpected endfor without matching for")
                node_stack.pop()
        
        if node_stack:
            raise TemplateSyntaxException(f"Unclosed block: {node_stack[-1]['type']}")
        
        return root_nodes
    
    def check_condition(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate if condition expression."""
        expr = expression.strip()
        
        # Direct variable check
        if expr in context:
            val = context[expr]
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return val != 0
            if isinstance(val, str):
                return bool(val.strip())
            if isinstance(val, (list, dict)):
                return bool(val)
            return bool(val)
        
        # Equality comparison
        if '==' in expr:
            left, right = expr.split('==', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) == right
        
        # Inequality comparison
        if '!=' in expr:
            left, right = expr.split('!=', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) != right
        
        return False
    
    def process_node(self, node: TemplateNode, data: Dict[str, Any]) -> str:
        """Process a single AST node."""
        if node.kind == TemplateNodeType.PLAIN_TEXT:
            return node.data
        
        elif node.kind == TemplateNodeType.VARIABLE:
            info = node.data
            value = data.get(info['name'], '')
            
            if value is None:
                value = ''
            else:
                value = str(value)
            
            for filter_name in info['filter_list']:
                if filter_name in self.filter_registry:
                    value = self.filter_registry[filter_name](value)
                else:
                    raise TemplateSyntaxException(f"Filter not found: {filter_name}")
            
            return value
        
        elif node.kind == TemplateNodeType.CONDITIONAL:
            expr = node.data['expression']
            if self.check_condition(expr, data):
                return ''.join(self.process_node(child, data) for child in node.inner_nodes)
            return ''
        
        elif node.kind == TemplateNodeType.LOOP:
            loop_info = node.data
            item_var = loop_info['item_name']
            collection_name = loop_info['list_name']
            
            collection = data.get(collection_name, [])
            if not isinstance(collection, (list, tuple)):
                collection = []
            
            output_parts = []
            for element in collection:
                new_data = data.copy()
                new_data[item_var] = element
                output_parts.append(
                    ''.join(self.process_node(child, new_data) for child in node.inner_nodes)
                )
            
            return ''.join(output_parts)
        
        return ''
    
    def compile(self, template: str) -> List[TemplateNode]:
        """Compile template to AST."""
        tokens = self.tokenize_template(template)
        return self.build_ast(tokens)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with provided data."""
        ast = self.compile(template)
        return ''.join(self.process_node(node, context) for node in ast)
    
    def register_filter(self, name: str, function: Callable[[str], str]) -> None:
        """Register a custom filter."""
        self.filter_registry[name] = function

def example_usage() -> None:
    """Demonstrate the template engine."""
    engine = RegexTemplateParser()
    
    sample_template = """
    <div class="profile">
        <h2>{{username|capitalize}}'s Profile</h2>
        
        {% if is_premium %}
        <p class="premium">Premium Member</p>
        {% endif %}
        
        <h3>Recent Posts:</h3>
        <ul>
        {% for post in posts %}
            <li>{{post.title|upper}} - {{post.date}}</li>
        {% endfor %}
        </ul>
    </div>
    """
    
    sample_data = {
        'username': 'alice smith',
        'is_premium': True,
        'posts': [
            {'title': 'Hello World', 'date': '2024-01-01'},
            {'title': 'Python Templates', 'date': '2024-01-02'},
            {'title': 'Regex Patterns', 'date': '2024-01-03'},
        ]
    }
    
    try:
        rendered = engine.render(sample_template, sample_data)
        print(rendered)
    except TemplateSyntaxException as err:
        print(f"Template error: {err}")

if __name__ == "__main__":
    example_usage()