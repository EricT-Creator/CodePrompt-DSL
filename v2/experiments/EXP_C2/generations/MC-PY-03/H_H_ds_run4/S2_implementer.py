import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

class NodeKind(Enum):
    TEXT = "text"
    VAR = "variable"
    IF = "if"
    FOR = "for"

@dataclass
class TemplateNode:
    kind: NodeKind
    value: Any
    children: List['TemplateNode']
    
    def __init__(self, kind: NodeKind, value: Any, children: Optional[List['TemplateNode']] = None):
        self.kind = kind
        self.value = value
        self.children = children if children is not None else []

class TemplateSyntaxError(Exception):
    """Exception for template syntax errors"""
    pass

class TemplateEngine:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.filter_map: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'strip': str.strip,
            'lstrip': str.lstrip,
            'rstrip': str.rstrip,
            'replace': lambda s, old=' ', new='_': s.replace(old, new),
        }
        
        # Compile regex patterns
        self.var_regex = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
        self.if_open_regex = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
        self.if_close_regex = re.compile(r'\{%\s*endif\s*%\}')
        self.for_open_regex = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
        self.for_close_regex = re.compile(r'\{%\s*endfor\s*%\}')
        self.tokenizer_regex = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter"""
        self.filter_map[name] = func
    
    def parse(self, source: str) -> TemplateNode:
        """Parse template source into AST"""
        root = TemplateNode(NodeKind.TEXT, "", [])
        node_stack: List[tuple[TemplateNode, Optional[str]]] = [(root, None)]
        
        # Split source into tokens
        tokens = self.tokenizer_regex.split(source)
        
        for token in tokens:
            if not token:
                continue
            
            current_node, block_type = node_stack[-1]
            
            # Check for variable
            var_match = self.var_regex.fullmatch(token)
            if var_match:
                var_content = var_match.group(1)
                if '|' in var_content:
                    var_name, *filters = var_content.split('|')
                else:
                    var_name, filters = var_content, []
                
                var_node = TemplateNode(
                    NodeKind.VAR,
                    {'name': var_name, 'filters': filters},
                    []
                )
                current_node.children.append(var_node)
                continue
            
            # Check for if start
            if_match = self.if_open_regex.fullmatch(token)
            if if_match:
                condition = if_match.group(1)
                if_node = TemplateNode(
                    NodeKind.IF,
                    {'condition': condition},
                    []
                )
                current_node.children.append(if_node)
                node_stack.append((if_node, 'if'))
                continue
            
            # Check for if end
            if self.if_close_regex.fullmatch(token):
                if not node_stack or node_stack[-1][1] != 'if':
                    raise TemplateSyntaxError("Unexpected endif")
                node_stack.pop()
                continue
            
            # Check for for start
            for_match = self.for_open_regex.fullmatch(token)
            if for_match:
                loop_var = for_match.group(1)
                iterable_name = for_match.group(2)
                for_node = TemplateNode(
                    NodeKind.FOR,
                    {'var': loop_var, 'iterable': iterable_name},
                    []
                )
                current_node.children.append(for_node)
                node_stack.append((for_node, 'for'))
                continue
            
            # Check for for end
            if self.for_close_regex.fullmatch(token):
                if not node_stack or node_stack[-1][1] != 'for':
                    raise TemplateSyntaxError("Unexpected endfor")
                node_stack.pop()
                continue
            
            # Plain text
            text_node = TemplateNode(NodeKind.TEXT, token, [])
            current_node.children.append(text_node)
        
        # Validate stack
        if len(node_stack) > 1:
            raise TemplateSyntaxError(f"Unclosed block: {node_stack[-1][1]}")
        
        return root
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate if condition"""
        condition = condition.strip()
        
        # Check if variable exists and is truthy
        if condition in context:
            val = context[condition]
            if isinstance(val, (list, dict, str)):
                return bool(val)
            return bool(val)
        
        # Try equality comparison
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            return context.get(left, '') == right
        
        # Try not-equal comparison
        if '!=' in condition:
            left, right = condition.split('!=', 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            return context.get(left, '') != right
        
        return False
    
    def _apply_filters(self, text: str, filters: List[str]) -> str:
        """Apply filter chain to text"""
        result = text
        for filter_name in filters:
            if filter_name not in self.filter_map:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            
            # Special handling for replace filter
            if filter_name == 'replace':
                result = self.filter_map[filter_name](result)
            else:
                result = self.filter_map[filter_name](result)
        
        return result
    
    def _render_node(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        """Render a single AST node"""
        if node.kind == NodeKind.TEXT:
            return str(node.value)
        
        elif node.kind == NodeKind.VAR:
            var_data = node.value
            var_name = var_data['name']
            filters = var_data['filters']
            
            if var_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined variable: {var_name}")
                return ""
            
            value = context[var_name]
            if not isinstance(value, str):
                value = str(value)
            
            return self._apply_filters(value, filters)
        
        elif node.kind == NodeKind.IF:
            if_data = node.value
            condition = if_data['condition']
            
            if self._evaluate_condition(condition, context):
                output_parts = []
                for child in node.children:
                    output_parts.append(self._render_node(child, context))
                return ''.join(output_parts)
            return ""
        
        elif node.kind == NodeKind.FOR:
            for_data = node.value
            loop_var = for_data['var']
            iterable_name = for_data['iterable']
            
            if iterable_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined iterable: {iterable_name}")
                return ""
            
            iterable = context[iterable_name]
            if not hasattr(iterable, '__iter__'):
                if self.strict:
                    raise TemplateSyntaxError(f"Not iterable: {iterable_name}")
                return ""
            
            result_parts = []
            for item in iterable:
                new_context = context.copy()
                new_context[loop_var] = item
                for child in node.children:
                    result_parts.append(self._render_node(child, new_context))
            
            return ''.join(result_parts)
        
        return ""
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        try:
            ast = self.parse(template)
            return self._render_node(ast, context)
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise TemplateSyntaxError(f"Rendering failed: {str(e)}")

# Demonstration
if __name__ == "__main__":
    engine = TemplateEngine(strict_mode=True)
    
    # Add custom filters
    engine.register_filter('reverse', lambda s: s[::-1])
    engine.register_filter('count_words', lambda s: str(len(s.split())))
    
    # Test template
    template = """
    <article class="blog-post">
        <header>
            <h1>{{post.title|title}}</h1>
            <p class="meta">By {{post.author|capitalize}} on {{post.date}}</p>
        </header>
        
        <div class="content">
            {{post.content}}
        </div>
        
        {% if post.tags %}
        <div class="tags">
            <h3>Tags:</h3>
            <ul>
                {% for tag in post.tags %}
                <li>{{tag|upper|replace}}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        <div class="stats">
            <p>Word count: {{post.content|count_words}}</p>
            {% if post.is_featured %}
            <span class="featured-badge">★ Featured</span>
            {% endif %}
        </div>
        
        {% if post.comments %}
        <div class="comments">
            <h3>Comments ({{post.comments|length}}):</h3>
            {% for comment in post.comments %}
            <div class="comment">
                <strong>{{comment.author|capitalize}}:</strong>
                <p>{{comment.text}}</p>
                <small>{{comment.timestamp}}</small>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </article>
    """
    
    context = {
        'post': {
            'title': 'introduction to template engines',
            'author': 'alice smith',
            'date': '2024-03-15',
            'content': 'Template engines are powerful tools for generating dynamic content. They separate presentation logic from business logic.',
            'tags': ['python', 'templating', 'web development'],
            'is_featured': True,
            'comments': [
                {
                    'author': 'bob',
                    'text': 'Great article! Very helpful.',
                    'timestamp': '2024-03-15 10:30'
                },
                {
                    'author': 'charlie',
                    'text': 'Could you add more examples?',
                    'timestamp': '2024-03-15 14:45'
                }
            ]
        }
    }
    
    try:
        output = engine.render(template, context)
        print("Rendered output:")
        print(output)
    except TemplateSyntaxError as e:
        print(f"Template error: {e}")