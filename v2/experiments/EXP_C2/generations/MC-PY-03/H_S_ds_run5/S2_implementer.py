import re
from typing import Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

class ASTNodeType(Enum):
    PLAIN = "plain"
    VARIABLE = "var"
    CONDITIONAL = "if"
    ITERATION = "for"

@dataclass
class ASTNode:
    node_type: ASTNodeType
    data: Any
    inner: List['ASTNode'] = field(default_factory=list)

class TemplateSyntaxException(Exception):
    """Exception for template syntax errors."""
    pass

class RegexTemplateEngine:
    """Regex-based template engine following the technical design constraints."""
    
    # Regex patterns from the technical design
    VARIABLE_REGEX = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_OPEN_REGEX = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    IF_CLOSE_REGEX = re.compile(r'\{%\s*endif\s*%\}')
    FOR_OPEN_REGEX = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_CLOSE_REGEX = re.compile(r'\{%\s*endfor\s*%\}')
    TOKEN_SPLIT_REGEX = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def __init__(self) -> None:
        """Initialize with default filter functions."""
        self.filter_registry: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
        }
    
    def split_into_tokens(self, template: str) -> List[Dict[str, Any]]:
        """Tokenize template using the master tokenizer regex."""
        tokens = []
        last_index = 0
        current_pos = 0
        
        for match in self.TOKEN_SPLIT_REGEX.finditer(template):
            # Add literal text before the match
            if last_index < match.start():
                literal_text = template[last_index:match.start()]
                tokens.append({'token_kind': 'literal', 'content': literal_text})
            
            tag_content = match.group()
            
            # Process variable tags
            if tag_content.startswith('{{'):
                var_match = self.VARIABLE_REGEX.match(tag_content)
                if not var_match:
                    raise TemplateSyntaxException(f"Invalid variable: {tag_content}")
                
                parts = var_match.group(1).split('|')
                variable_name = parts[0]
                filter_names = parts[1:] if len(parts) > 1 else []
                
                tokens.append({
                    'token_kind': 'variable',
                    'name': variable_name,
                    'filters': filter_names,
                    'raw': tag_content
                })
            
            # Process if opening tags
            elif tag_content.startswith('{% if'):
                if_match = self.IF_OPEN_REGEX.match(tag_content)
                if not if_match:
                    raise TemplateSyntaxException(f"Invalid if: {tag_content}")
                
                tokens.append({
                    'token_kind': 'if_start',
                    'condition': if_match.group(1),
                    'raw': tag_content
                })
            
            # Process if closing tags
            elif tag_content == '{% endif %}':
                tokens.append({'token_kind': 'if_end', 'raw': tag_content})
            
            # Process for opening tags
            elif tag_content.startswith('{% for'):
                for_match = self.FOR_OPEN_REGEX.match(tag_content)
                if not for_match:
                    raise TemplateSyntaxException(f"Invalid for: {tag_content}")
                
                tokens.append({
                    'token_kind': 'for_start',
                    'item_var': for_match.group(1),
                    'list_var': for_match.group(2),
                    'raw': tag_content
                })
            
            # Process for closing tags
            elif tag_content == '{% endfor %}':
                tokens.append({'token_kind': 'for_end', 'raw': tag_content})
            
            else:
                raise TemplateSyntaxException(f"Unknown template directive: {tag_content}")
            
            last_index = match.end()
        
        # Add any remaining literal text
        if last_index < len(template):
            tokens.append({'token_kind': 'literal', 'content': template[last_index:]})
        
        return tokens
    
    def build_ast_from_tokens(self, tokens: List[Dict[str, Any]]) -> List[ASTNode]:
        """Build AST using stack-based recursive descent approach."""
        root_nodes = []
        context_stack = []
        
        for token in tokens:
            if token['token_kind'] == 'literal':
                new_node = ASTNode(ASTNodeType.PLAIN, token['content'])
                if context_stack:
                    context_stack[-1]['node'].inner.append(new_node)
                else:
                    root_nodes.append(new_node)
            
            elif token['token_kind'] == 'variable':
                var_node = ASTNode(
                    ASTNodeType.VARIABLE,
                    {'var_name': token['name'], 'filter_chain': token['filters']}
                )
                if context_stack:
                    context_stack[-1]['node'].inner.append(var_node)
                else:
                    root_nodes.append(var_node)
            
            elif token['token_kind'] == 'if_start':
                if_node = ASTNode(ASTNodeType.CONDITIONAL, {'expression': token['condition']})
                if context_stack:
                    context_stack[-1]['node'].inner.append(if_node)
                else:
                    root_nodes.append(if_node)
                context_stack.append({'type': 'if', 'node': if_node})
            
            elif token['token_kind'] == 'if_end':
                if not context_stack or context_stack[-1]['type'] != 'if':
                    raise TemplateSyntaxException("Unexpected endif without matching if")
                context_stack.pop()
            
            elif token['token_kind'] == 'for_start':
                for_node = ASTNode(
                    ASTNodeType.ITERATION,
                    {'loop_var': token['item_var'], 'collection': token['list_var']}
                )
                if context_stack:
                    context_stack[-1]['node'].inner.append(for_node)
                else:
                    root_nodes.append(for_node)
                context_stack.append({'type': 'for', 'node': for_node})
            
            elif token['token_kind'] == 'for_end':
                if not context_stack or context_stack[-1]['type'] != 'for':
                    raise TemplateSyntaxException("Unexpected endfor without matching for")
                context_stack.pop()
        
        if context_stack:
            raise TemplateSyntaxException(f"Unclosed {context_stack[-1]['type']} block")
        
        return root_nodes
    
    def evaluate_if_expression(self, expression: str, data: Dict[str, Any]) -> bool:
        """Evaluate if condition with simple truthy checks and basic comparisons."""
        expr = expression.strip()
        
        # Direct variable truthiness
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
    
    def process_ast_node(self, node: ASTNode, context: Dict[str, Any]) -> str:
        """Process a single AST node to generate output."""
        if node.node_type == ASTNodeType.PLAIN:
            return node.data
        
        elif node.node_type == ASTNodeType.VARIABLE:
            var_info = node.data
            value = context.get(var_info['var_name'], '')
            
            # Convert to string
            if value is None:
                value = ''
            else:
                value = str(value)
            
            # Apply filters sequentially
            for filter_name in var_info['filter_chain']:
                if filter_name in self.filter_registry:
                    value = self.filter_registry[filter_name](value)
                else:
                    raise TemplateSyntaxException(f"Unknown filter: {filter_name}")
            
            return value
        
        elif node.node_type == ASTNodeType.CONDITIONAL:
            expr = node.data['expression']
            if self.evaluate_if_expression(expr, context):
                return ''.join(self.process_ast_node(child, context) for child in node.inner)
            return ''
        
        elif node.node_type == ASTNodeType.ITERATION:
            loop_info = node.data
            loop_var = loop_info['loop_var']
            collection_name = loop_info['collection']
            
            collection = context.get(collection_name, [])
            if not isinstance(collection, (list, tuple)):
                collection = []
            
            output_segments = []
            for item in collection:
                new_context = context.copy()
                new_context[loop_var] = item
                output_segments.append(
                    ''.join(self.process_ast_node(child, new_context) for child in node.inner)
                )
            
            return ''.join(output_segments)
        
        return ''
    
    def compile_template(self, template: str) -> List[ASTNode]:
        """Compile template string to AST."""
        tokens = self.split_into_tokens(template)
        return self.build_ast_from_tokens(tokens)
    
    def render(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with provided data context."""
        ast = self.compile_template(template)
        return ''.join(self.process_ast_node(node, data) for node in ast)
    
    def register_filter(self, name: str, function: Callable[[str], str]) -> None:
        """Register a custom filter function."""
        self.filter_registry[name] = function

def demonstrate_engine() -> None:
    """Demonstrate the template engine with an example."""
    engine = RegexTemplateEngine()
    
    example_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{{site_name|title}} - {{page_title|capitalize}}</title>
    </head>
    <body>
        <header>
            <h1>{{site_name|upper}}</h1>
            <nav>
                <ul>
                {% for link in nav_links %}
                    <li><a href="{{link.url}}">{{link.text|capitalize}}</a></li>
                {% endfor %}
                </ul>
            </nav>
        </header>
        
        <main>
            <h2>{{page_title}}</h2>
            
            {% if user_logged_in %}
            <div class="user-info">
                <p>Welcome back, <strong>{{username|title}}</strong>!</p>
                {% if unread_count > 0 %}
                <p class="notification">You have {{unread_count}} unread messages.</p>
                {% endif %}
            </div>
            {% endif %}
            
            <section class="content">
                {{main_content}}
            </section>
            
            <section class="products">
                <h3>Featured Products:</h3>
                <div class="product-grid">
                {% for product in featured_products %}
                    <div class="product-card">
                        <h4>{{product.name|title}}</h4>
                        <p class="price">${{product.price}}</p>
                        <p class="description">{{product.description|capitalize}}</p>
                    </div>
                {% endfor %}
                </div>
            </section>
        </main>
        
        <footer>
            <p>&copy; {{current_year}} {{site_name}}. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    example_data = {
        'site_name': 'my online store',
        'page_title': 'home page',
        'nav_links': [
            {'url': '/', 'text': 'home'},
            {'url': '/products', 'text': 'products'},
            {'url': '/about', 'text': 'about us'},
            {'url': '/contact', 'text': 'contact'},
        ],
        'user_logged_in': True,
        'username': 'john_doe',
        'unread_count': 5,
        'main_content': 'Welcome to our online store! We offer a wide range of products...',
        'featured_products': [
            {'name': 'wireless headphones', 'price': 129.99, 'description': 'noise-cancelling wireless headphones'},
            {'name': 'smart watch', 'price': 299.99, 'description': 'fitness tracker with heart rate monitor'},
            {'name': 'laptop stand', 'price': 49.99, 'description': 'adjustable ergonomic laptop stand'},
        ],
        'current_year': 2024
    }
    
    try:
        output = engine.render(example_template, example_data)
        print(output)
    except TemplateSyntaxException as error:
        print(f"Template error: {error}")

if __name__ == "__main__":
    demonstrate_engine()