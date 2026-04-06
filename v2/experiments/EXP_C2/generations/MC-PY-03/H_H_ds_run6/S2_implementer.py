import re
from typing import Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

class NodeType(Enum):
    TEXT = "text"
    VARIABLE = "var"
    IF_BLOCK = "if"
    FOR_BLOCK = "for"

@dataclass
class ASTNode:
    node_type: NodeType
    content: Any
    children: List['ASTNode'] = field(default_factory=list)

class TemplateSyntaxError(Exception):
    """Exception raised for template syntax errors."""
    pass

class RegexTemplateEngine:
    """Regex-based template engine as per technical design."""
    
    # Regex patterns from design document
    VAR_PATTERN = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_OPEN_PATTERN = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    IF_CLOSE_PATTERN = re.compile(r'\{%\s*endif\s*%\}')
    FOR_OPEN_PATTERN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_CLOSE_PATTERN = re.compile(r'\{%\s*endfor\s*%\}')
    TOKEN_PATTERN = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize engine with default filters."""
        self.filter_map: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'strip': str.strip,
        }
    
    def tokenize(self, template: str) -> List[Dict[str, Any]]:
        """Tokenize template into literal and control tokens."""
        tokens = []
        last_pos = 0
        current_pos = 0
        
        for match in self.TOKEN_PATTERN.finditer(template):
            # Add literal text before the match
            if last_pos < match.start():
                literal = template[last_pos:match.start()]
                tokens.append({'type': 'literal', 'text': literal})
            
            tag = match.group()
            
            # Variable substitution
            if tag.startswith('{{'):
                var_match = self.VAR_PATTERN.match(tag)
                if not var_match:
                    raise TemplateSyntaxError(f"Invalid variable: {tag}")
                
                parts = var_match.group(1).split('|')
                variable = parts[0]
                filters = parts[1:] if len(parts) > 1 else []
                
                tokens.append({
                    'type': 'variable',
                    'name': variable,
                    'filters': filters,
                    'raw': tag
                })
            
            # If statement opening
            elif tag.startswith('{% if'):
                if_match = self.IF_OPEN_PATTERN.match(tag)
                if not if_match:
                    raise TemplateSyntaxError(f"Invalid if: {tag}")
                
                tokens.append({
                    'type': 'if_start',
                    'condition': if_match.group(1),
                    'raw': tag
                })
            
            # If statement closing
            elif tag == '{% endif %}':
                tokens.append({'type': 'if_end', 'raw': tag})
            
            # For loop opening
            elif tag.startswith('{% for'):
                for_match = self.FOR_OPEN_PATTERN.match(tag)
                if not for_match:
                    raise TemplateSyntaxError(f"Invalid for: {tag}")
                
                tokens.append({
                    'type': 'for_start',
                    'var': for_match.group(1),
                    'iterable': for_match.group(2),
                    'raw': tag
                })
            
            # For loop closing
            elif tag == '{% endfor %}':
                tokens.append({'type': 'for_end', 'raw': tag})
            
            else:
                raise TemplateSyntaxError(f"Unknown tag: {tag}")
            
            last_pos = match.end()
        
        # Add remaining literal text
        if last_pos < len(template):
            tokens.append({'type': 'literal', 'text': template[last_pos:]})
        
        return tokens
    
    def parse_ast(self, tokens: List[Dict[str, Any]]) -> List[ASTNode]:
        """Parse tokens into AST using stack-based recursive descent."""
        root_nodes = []
        stack = []
        
        for token in tokens:
            if token['type'] == 'literal':
                node = ASTNode(NodeType.TEXT, token['text'])
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
            
            elif token['type'] == 'variable':
                node = ASTNode(
                    NodeType.VARIABLE,
                    {'var_name': token['name'], 'filter_list': token['filters']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
            
            elif token['type'] == 'if_start':
                node = ASTNode(NodeType.IF_BLOCK, {'condition': token['condition']})
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
                stack.append({'type': 'if', 'node': node})
            
            elif token['type'] == 'if_end':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateSyntaxError("Unexpected endif")
                stack.pop()
            
            elif token['type'] == 'for_start':
                node = ASTNode(
                    NodeType.FOR_BLOCK,
                    {'item_var': token['var'], 'list_name': token['iterable']}
                )
                if stack:
                    stack[-1]['node'].children.append(node)
                else:
                    root_nodes.append(node)
                stack.append({'type': 'for', 'node': node})
            
            elif token['type'] == 'for_end':
                if not stack or stack[-1]['type'] != 'for':
                    raise TemplateSyntaxError("Unexpected endfor")
                stack.pop()
        
        if stack:
            raise TemplateSyntaxError(f"Unclosed {stack[-1]['type']} block")
        
        return root_nodes
    
    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate if condition with simple truthy checks and comparisons."""
        cond = condition.strip()
        
        # Direct variable truth test
        if cond in context:
            val = context[cond]
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
        if '==' in cond:
            left, right = cond.split('==', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) == right
        
        # Inequality comparison
        if '!=' in cond:
            left, right = cond.split('!=', 1)
            left = left.strip()
            right = right.strip().strip('"\'')
            return str(context.get(left, '')) != right
        
        return False
    
    def render_node(self, node: ASTNode, data: Dict[str, Any]) -> str:
        """Render a single AST node."""
        if node.node_type == NodeType.TEXT:
            return node.content
        
        elif node.node_type == NodeType.VARIABLE:
            info = node.content
            value = data.get(info['var_name'], '')
            
            if value is None:
                value = ''
            else:
                value = str(value)
            
            for filter_name in info['filter_list']:
                if filter_name in self.filter_map:
                    value = self.filter_map[filter_name](value)
                else:
                    raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            
            return value
        
        elif node.node_type == NodeType.IF_BLOCK:
            condition = node.content['condition']
            if self.evaluate_condition(condition, data):
                return ''.join(self.render_node(child, data) for child in node.children)
            return ''
        
        elif node.node_type == NodeType.FOR_BLOCK:
            loop_info = node.content
            item_var = loop_info['item_var']
            list_name = loop_info['list_name']
            
            items = data.get(list_name, [])
            if not isinstance(items, (list, tuple)):
                items = []
            
            result = []
            for item in items:
                new_data = data.copy()
                new_data[item_var] = item
                result.append(''.join(self.render_node(child, new_data) for child in node.children))
            
            return ''.join(result)
        
        return ''
    
    def compile(self, template: str) -> List[ASTNode]:
        """Compile template to AST."""
        tokens = self.tokenize(template)
        return self.parse_ast(tokens)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context."""
        ast = self.compile(template)
        return ''.join(self.render_node(node, context) for node in ast)
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Add a custom filter."""
        self.filter_map[name] = func

def example() -> None:
    """Example usage of the template engine."""
    engine = RegexTemplateEngine()
    
    sample = """
    <article class="post">
        <header>
            <h1>{{post.title|capitalize}}</h1>
            <div class="meta">
                By <strong>{{post.author|title}}</strong>
                on <em>{{post.date}}</em>
            </div>
        </header>
        
        <div class="content">
            {{post.content}}
        </div>
        
        {% if post.tags %}
        <footer>
            <h3>Tags:</h3>
            <ul class="tags">
            {% for tag in post.tags %}
                <li>{{tag|upper}}</li>
            {% endfor %}
            </ul>
        </footer>
        {% endif %}
        
        {% if post.comments_enabled %}
        <section class="comments">
            <h3>Comments ({{post.comment_count}})</h3>
            {% for comment in post.comments %}
            <div class="comment">
                <strong>{{comment.author}}</strong> said:
                <p>{{comment.text}}</p>
            </div>
            {% endfor %}
        </section>
        {% endif %}
    </article>
    """
    
    data = {
        'post': {
            'title': 'introduction to template engines',
            'author': 'jane smith',
            'date': '2024-03-15',
            'content': 'This is a sample blog post about template engines...',
            'tags': ['python', 'templates', 'web'],
            'comments_enabled': True,
            'comment_count': 2,
            'comments': [
                {'author': 'Alice', 'text': 'Great article!'},
                {'author': 'Bob', 'text': 'Very informative.'},
            ]
        }
    }
    
    try:
        rendered = engine.render(sample, data)
        print(rendered)
    except TemplateSyntaxError as e:
        print(f"Template error: {e}")

if __name__ == "__main__":
    example()