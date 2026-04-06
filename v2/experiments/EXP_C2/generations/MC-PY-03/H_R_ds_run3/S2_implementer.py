import re
from typing import Dict, List, Optional, Union, Any, Callable
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
    """Custom exception for template syntax errors"""
    pass

class TemplateEngine:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.filters: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'strip': str.strip,
            'lstrip': str.lstrip,
            'rstrip': str.rstrip,
        }
        
        # Regex patterns
        self.var_pattern = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
        self.if_open_pattern = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
        self.if_close_pattern = re.compile(r'\{%\s*endif\s*%\}')
        self.for_open_pattern = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
        self.for_close_pattern = re.compile(r'\{%\s*endfor\s*%\}')
        self.tokenizer_pattern = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Add a custom filter"""
        self.filters[name] = func
    
    def parse(self, template: str) -> Node:
        """Parse template into AST"""
        root = Node(NodeType.TEXT, "", [])
        stack = [(root, None)]  # (parent_node, block_type)
        
        # Tokenize
        parts = self.tokenizer_pattern.split(template)
        
        for part in parts:
            if not part:
                continue
                
            current_parent, _ = stack[-1]
            
            # Check for variable
            var_match = self.var_pattern.fullmatch(part)
            if var_match:
                var_content = var_match.group(1)
                if '|' in var_content:
                    var_name, *filters = var_content.split('|')
                    node = Node(NodeType.VARIABLE, {'name': var_name, 'filters': filters})
                else:
                    node = Node(NodeType.VARIABLE, {'name': var_content, 'filters': []})
                current_parent.children.append(node)
                continue
            
            # Check for if open
            if_match = self.if_open_pattern.fullmatch(part)
            if if_match:
                condition = if_match.group(1)
                if_node = Node(NodeType.IF, {'condition': condition}, [])
                current_parent.children.append(if_node)
                stack.append((if_node, 'if'))
                continue
            
            # Check for if close
            if self.if_close_pattern.fullmatch(part):
                if not stack or stack[-1][1] != 'if':
                    raise TemplateSyntaxError("Unexpected endif")
                stack.pop()
                continue
            
            # Check for for open
            for_match = self.for_open_pattern.fullmatch(part)
            if for_match:
                loop_var = for_match.group(1)
                iterable_name = for_match.group(2)
                for_node = Node(NodeType.FOR, {'var': loop_var, 'iterable': iterable_name}, [])
                current_parent.children.append(for_node)
                stack.append((for_node, 'for'))
                continue
            
            # Check for for close
            if self.for_close_pattern.fullmatch(part):
                if not stack or stack[-1][1] != 'for':
                    raise TemplateSyntaxError("Unexpected endfor")
                stack.pop()
                continue
            
            # Literal text
            node = Node(NodeType.TEXT, part)
            current_parent.children.append(node)
        
        # Check for unclosed blocks
        if len(stack) > 1:
            raise TemplateSyntaxError(f"Unclosed block: {stack[-1][1]}")
        
        return root
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate if condition"""
        # Simple truthy check
        if condition in context:
            value = context[condition]
            if isinstance(value, (list, dict, str)):
                return bool(value)
            return bool(value)
        
        # Try comparison
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            return context.get(left, '') == right
        
        return False
    
    def _apply_filters(self, value: str, filters: List[str]) -> str:
        """Apply filters to value"""
        result = value
        for filter_name in filters:
            if filter_name not in self.filters:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            result = self.filters[filter_name](result)
        return result
    
    def _render_node(self, node: Node, context: Dict[str, Any]) -> str:
        """Render a single node"""
        if node.node_type == NodeType.TEXT:
            return str(node.content)
        
        elif node.node_type == NodeType.VARIABLE:
            var_info = node.content
            var_name = var_info['name']
            filters = var_info['filters']
            
            if var_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined variable: {var_name}")
                return ""
            
            value = context[var_name]
            if not isinstance(value, str):
                value = str(value)
            
            return self._apply_filters(value, filters)
        
        elif node.node_type == NodeType.IF:
            condition = node.content['condition']
            if self._evaluate_condition(condition, context):
                result = []
                for child in node.children:
                    result.append(self._render_node(child, context))
                return ''.join(result)
            return ""
        
        elif node.node_type == NodeType.FOR:
            var_info = node.content
            loop_var = var_info['var']
            iterable_name = var_info['iterable']
            
            if iterable_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined iterable: {iterable_name}")
                return ""
            
            iterable = context[iterable_name]
            if not hasattr(iterable, '__iter__'):
                if self.strict:
                    raise TemplateSyntaxError(f"Not iterable: {iterable_name}")
                return ""
            
            result = []
            for item in iterable:
                new_context = context.copy()
                new_context[loop_var] = item
                for child in node.children:
                    result.append(self._render_node(child, new_context))
            
            return ''.join(result)
        
        return ""
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        try:
            ast = self.parse(template)
            return self._render_node(ast, context)
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise TemplateSyntaxError(f"Rendering error: {str(e)}")

# Example usage
if __name__ == "__main__":
    engine = TemplateEngine()
    
    # Test template
    template = """
    <h1>Hello {{name|capitalize}}!</h1>
    {% if show_list %}
    <ul>
        {% for item in items %}
        <li>{{item|upper}}</li>
        {% endfor %}
    </ul>
    {% endif %}
    """
    
    context = {
        'name': 'world',
        'show_list': True,
        'items': ['apple', 'banana', 'cherry']
    }
    
    try:
        result = engine.render(template, context)
        print(result)
    except TemplateSyntaxError as e:
        print(f"Template error: {e}")