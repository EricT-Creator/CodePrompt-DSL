import re
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass
from enum import Enum

class NodeKind(Enum):
    TEXT = 1
    VAR = 2
    IF = 3
    FOR = 4

@dataclass
class TemplateNode:
    kind: NodeKind
    value: Any
    children: List['TemplateNode'] = None
    
    def __init__(self, kind: NodeKind, value: Any, children: List['TemplateNode'] = None):
        self.kind = kind
        self.value = value
        self.children = children if children is not None else []

class TemplateError(Exception):
    """Base exception for template errors"""
    pass

class TemplateSyntaxError(TemplateError):
    """Syntax error in template"""
    pass

class TemplateEngine:
    def __init__(self, strict_mode: bool = False):
        self.strict = strict_mode
        self.filter_registry: Dict[str, Callable[[str], str]] = {
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'capitalize': lambda s: s.capitalize(),
            'strip': lambda s: s.strip(),
            'lstrip': lambda s: s.lstrip(),
            'rstrip': lambda s: s.rstrip(),
            'title': lambda s: s.title(),
            'replace': lambda s, old='', new='': s.replace(old, new),
        }
        
        # Compile regex patterns
        self.var_re = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
        self.if_open_re = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
        self.if_close_re = re.compile(r'\{%\s*endif\s*%\}')
        self.for_open_re = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
        self.for_close_re = re.compile(r'\{%\s*endfor\s*%\}')
        self.token_re = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})')
    
    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter"""
        self.filter_registry[name] = func
    
    def parse_template(self, source: str) -> TemplateNode:
        """Parse template source into AST"""
        root = TemplateNode(NodeKind.TEXT, '', [])
        stack: List[tuple[TemplateNode, str]] = [(root, None)]
        
        # Split template into tokens
        tokens = self.token_re.split(source)
        
        for token in tokens:
            if not token:
                continue
            
            current_parent, block_type = stack[-1]
            
            # Variable substitution
            var_match = self.var_re.fullmatch(token)
            if var_match:
                var_content = var_match.group(1)
                if '|' in var_content:
                    var_name, *filters = var_content.split('|')
                else:
                    var_name, filters = var_content, []
                var_node = TemplateNode(NodeKind.VAR, {'var': var_name, 'filters': filters})
                current_parent.children.append(var_node)
                continue
            
            # If block start
            if_match = self.if_open_re.fullmatch(token)
            if if_match:
                condition = if_match.group(1)
                if_node = TemplateNode(NodeKind.IF, {'cond': condition}, [])
                current_parent.children.append(if_node)
                stack.append((if_node, 'if'))
                continue
            
            # If block end
            if self.if_close_re.fullmatch(token):
                if not stack or stack[-1][1] != 'if':
                    raise TemplateSyntaxError("Unexpected endif")
                stack.pop()
                continue
            
            # For block start
            for_match = self.for_open_re.fullmatch(token)
            if for_match:
                loop_var = for_match.group(1)
                iter_name = for_match.group(2)
                for_node = TemplateNode(NodeKind.FOR, {'var': loop_var, 'iter': iter_name}, [])
                current_parent.children.append(for_node)
                stack.append((for_node, 'for'))
                continue
            
            # For block end
            if self.for_close_re.fullmatch(token):
                if not stack or stack[-1][1] != 'for':
                    raise TemplateSyntaxError("Unexpected endfor")
                stack.pop()
                continue
            
            # Plain text
            text_node = TemplateNode(NodeKind.TEXT, token)
            current_parent.children.append(text_node)
        
        # Check for unclosed blocks
        if len(stack) > 1:
            raise TemplateSyntaxError(f"Unclosed block: {stack[-1][1]}")
        
        return root
    
    def _evaluate_condition(self, condition: str, ctx: Dict[str, Any]) -> bool:
        """Evaluate if condition expression"""
        condition = condition.strip()
        
        # Check if variable exists and is truthy
        if condition in ctx:
            val = ctx[condition]
            if isinstance(val, (list, dict, str)):
                return bool(val)
            return bool(val)
        
        # Simple equality check
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            return ctx.get(left, '') == right
        
        # Not-equal check
        if '!=' in condition:
            left, right = condition.split('!=', 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            return ctx.get(left, '') != right
        
        return False
    
    def _apply_filters(self, text: str, filters: List[str]) -> str:
        """Apply filter chain to text"""
        result = text
        for fname in filters:
            if fname not in self.filter_registry:
                raise TemplateSyntaxError(f"Unknown filter: {fname}")
            # Special handling for replace filter
            if fname == 'replace':
                # Default replacement
                result = self.filter_registry[fname](result, ' ', '_')
            else:
                result = self.filter_registry[fname](result)
        return result
    
    def _render_node(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        """Render a single AST node"""
        if node.kind == NodeKind.TEXT:
            return str(node.value)
        
        elif node.kind == NodeKind.VAR:
            var_info = node.value
            var_name = var_info['var']
            filters = var_info['filters']
            
            if var_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined variable: {var_name}")
                return ''
            
            value = context[var_name]
            if not isinstance(value, str):
                value = str(value)
            
            return self._apply_filters(value, filters)
        
        elif node.kind == NodeKind.IF:
            cond_info = node.value
            condition = cond_info['cond']
            
            if self._evaluate_condition(condition, context):
                output = []
                for child in node.children:
                    output.append(self._render_node(child, context))
                return ''.join(output)
            return ''
        
        elif node.kind == NodeKind.FOR:
            for_info = node.value
            loop_var = for_info['var']
            iter_name = for_info['iter']
            
            if iter_name not in context:
                if self.strict:
                    raise TemplateSyntaxError(f"Undefined iterable: {iter_name}")
                return ''
            
            iterable = context[iter_name]
            if not hasattr(iterable, '__iter__'):
                if self.strict:
                    raise TemplateSyntaxError(f"Not iterable: {iter_name}")
                return ''
            
            result = []
            for item in iterable:
                new_ctx = context.copy()
                new_ctx[loop_var] = item
                for child in node.children:
                    result.append(self._render_node(child, new_ctx))
            
            return ''.join(result)
        
        return ''
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with given context"""
        try:
            ast_root = self.parse_template(template)
            return self._render_node(ast_root, context)
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise TemplateSyntaxError(f"Render failed: {e}")

# Usage example
if __name__ == "__main__":
    engine = TemplateEngine(strict_mode=True)
    
    # Add custom filter
    engine.register_filter('reverse', lambda s: s[::-1])
    
    template = """
    <div class="user-profile">
        <h2>{{username|capitalize}}</h2>
        <p>Email: {{email}}</p>
        
        {% if has_items %}
        <h3>Items:</h3>
        <ul>
            {% for item in items %}
            <li>{{item|upper|reverse}}</li>
            {% endfor %}
        </ul>
        {% endif %}
        
        {% if is_admin %}
        <p class="admin">Admin Access</p>
        {% endif %}
    </div>
    """
    
    context = {
        'username': 'john_doe',
        'email': 'john@example.com',
        'has_items': True,
        'items': ['apple', 'banana', 'cherry'],
        'is_admin': False,
    }
    
    try:
        output = engine.render(template, context)
        print(output)
    except TemplateSyntaxError as e:
        print(f"Error: {e}")