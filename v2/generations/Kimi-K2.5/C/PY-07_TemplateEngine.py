import re
from typing import Dict, Any, List, Callable


class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""
    pass


class TemplateEngine:
    """A simple template engine supporting variables, conditionals, and loops."""
    
    FILTERS: Dict[str, Callable[[Any], str]] = {
        'upper': lambda x: str(x).upper(),
        'lower': lambda x: str(x).lower(),
        'title': lambda x: str(x).title(),
    }
    
    def __init__(self):
        self.token_pattern = re.compile(
            r'\{\{\s*(.+?)\s*\}\}|'  # {{ variable }}
            r'\{%\s*if\s+(.+?)\s*%\}|'  # {% if condition %}
            r'\{%\s*endif\s*%\}|'  # {% endif %}
            r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}|'  # {% for x in list %}
            r'\{%\s*endfor\s*%\}',  # {% endfor %}
            re.DOTALL
        )
    
    def _parse_filters(self, var_expr: str) -> tuple:
        """Parse variable expression with optional filters."""
        parts = var_expr.split('|')
        var_name = parts[0].strip()
        filters = [f.strip() for f in parts[1:]]
        return var_name, filters
    
    def _apply_filters(self, value: Any, filters: List[str]) -> str:
        """Apply filters to a value."""
        result = str(value)
        for filter_name in filters:
            if filter_name in self.FILTERS:
                result = self.FILTERS[filter_name](result)
            else:
                raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")
        return result
    
    def _get_value(self, var_name: str, context: Dict[str, Any]) -> Any:
        """Get value from context, supporting dot notation."""
        parts = var_name.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                value = None
            
            if value is None:
                return None
        
        return value
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple condition."""
        condition = condition.strip()
        
        # Handle 'not' prefix
        negate = False
        if condition.startswith('not '):
            negate = True
            condition = condition[4:].strip()
        
        # Handle comparisons
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._get_value(left.strip(), context)
                right_val = self._parse_literal(right.strip())
                
                if op == '==':
                    result = left_val == right_val
                elif op == '!=':
                    result = left_val != right_val
                elif op == '>=':
                    result = left_val is not None and right_val is not None and left_val >= right_val
                elif op == '<=':
                    result = left_val is not None and right_val is not None and left_val <= right_val
                elif op == '>':
                    result = left_val is not None and right_val is not None and left_val > right_val
                elif op == '<':
                    result = left_val is not None and right_val is not None and left_val < right_val
                
                return not result if negate else result
        
        # Simple truthiness check
        value = self._get_value(condition, context)
        result = bool(value)
        return not result if negate else result
    
    def _parse_literal(self, value: str) -> Any:
        """Parse a literal value from string."""
        value = value.strip()
        
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        try:
            return int(value)
        except ValueError:
            pass
        
        try:
            return float(value)
        except ValueError:
            pass
        
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'none':
            return None
        
        return value
    
    def _tokenize(self, template: str) -> List[tuple]:
        """Tokenize the template into structured blocks."""
        tokens = []
        pos = 0
        
        while pos < len(template):
            match = self.token_pattern.search(template, pos)
            
            if not match:
                # Add remaining text
                if pos < len(template):
                    tokens.append(('text', template[pos:]))
                break
            
            # Add text before the match
            if match.start() > pos:
                tokens.append(('text', template[pos:match.start()]))
            
            # Determine token type
            if match.group(1):  # {{ variable }}
                var_expr = match.group(1)
                var_name, filters = self._parse_filters(var_expr)
                tokens.append(('var', var_name, filters))
            elif match.group(2):  # {% if condition %}
                tokens.append(('if', match.group(2)))
            elif match.group(3):  # {% for var in list %}
                tokens.append(('for', match.group(3), match.group(4)))
            elif '{% endif %}' in match.group(0):
                tokens.append(('endif',))
            elif '{% endfor %}' in match.group(0):
                tokens.append(('endfor',))
            
            pos = match.end()
        
        return tokens
    
    def _build_ast(self, tokens: List[tuple]) -> List[dict]:
        """Build an abstract syntax tree from tokens."""
        ast = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token[0] == 'text':
                ast.append({'type': 'text', 'content': token[1]})
            
            elif token[0] == 'var':
                ast.append({'type': 'var', 'name': token[1], 'filters': token[2]})
            
            elif token[0] == 'if':
                # Find matching endif
                depth = 1
                j = i + 1
                while j < len(tokens) and depth > 0:
                    if tokens[j][0] == 'if':
                        depth += 1
                    elif tokens[j][0] == 'endif':
                        depth -= 1
                    j += 1
                
                if depth > 0:
                    raise TemplateSyntaxError("Unclosed 'if' block")
                
                ast.append({
                    'type': 'if',
                    'condition': token[1],
                    'body': self._build_ast(tokens[i+1:j-1])
                })
                i = j - 1
            
            elif token[0] == 'for':
                # Find matching endfor
                depth = 1
                j = i + 1
                while j < len(tokens) and depth > 0:
                    if tokens[j][0] == 'for':
                        depth += 1
                    elif tokens[j][0] == 'endfor':
                        depth -= 1
                    j += 1
                
                if depth > 0:
                    raise TemplateSyntaxError("Unclosed 'for' block")
                
                ast.append({
                    'type': 'for',
                    'var': token[1],
                    'iterable': token[2],
                    'body': self._build_ast(tokens[i+1:j-1])
                })
                i = j - 1
            
            i += 1
        
        return ast
    
    def _render_ast(self, ast: List[dict], context: Dict[str, Any]) -> str:
        """Render the AST with the given context."""
        result = []
        
        for node in ast:
            if node['type'] == 'text':
                result.append(node['content'])
            
            elif node['type'] == 'var':
                value = self._get_value(node['name'], context)
                if value is None:
                    value = ''
                result.append(self._apply_filters(value, node['filters']))
            
            elif node['type'] == 'if':
                if self._evaluate_condition(node['condition'], context):
                    result.append(self._render_ast(node['body'], context))
            
            elif node['type'] == 'for':
                iterable = self._get_value(node['iterable'], context)
                if iterable is None:
                    continue
                
                for item in iterable:
                    loop_context = context.copy()
                    loop_context[node['var']] = item
                    result.append(self._render_ast(node['body'], loop_context))
        
        return ''.join(result)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context."""
        try:
            tokens = self._tokenize(template)
            ast = self._build_ast(tokens)
            return self._render_ast(ast, context)
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise TemplateSyntaxError(f"Error rendering template: {e}")


def main():
    """Example usage of TemplateEngine."""
    engine = TemplateEngine()
    
    # Example 1: Variables and filters
    template1 = "Hello, {{ name|title }}!"
    context1 = {"name": "john doe"}
    result1 = engine.render(template1, context1)
    print(f"Template: {template1}")
    print(f"Context: {context1}")
    print(f"Result: {result1}")
    print()
    
    # Example 2: Conditionals
    template2 = """
{% if user %}
Welcome back, {{ user|upper }}!
{% endif %}
{% if not user %}
Please log in.
{% endif %}
""".strip()
    context2 = {"user": "alice"}
    result2 = engine.render(template2, context2)
    print(f"Template:\n{template2}")
    print(f"Context: {context2}")
    print(f"Result:\n{result2}")
    print()
    
    # Example 3: Loops
    template3 = """
Items:
{% for item in items %}
- {{ item.name }}: ${{ item.price }}
{% endfor %}
""".strip()
    context3 = {
        "items": [
            {"name": "Apple", "price": 1.50},
            {"name": "Banana", "price": 0.75},
            {"name": "Cherry", "price": 3.00}
        ]
    }
    result3 = engine.render(template3, context3)
    print(f"Template:\n{template3}")
    print(f"Context: {context3}")
    print(f"Result:\n{result3}")
    print()
    
    # Example 4: Nested blocks
    template4 = """
{% if show_list %}
Users:
{% for user in users %}
{% if user.active %}
- {{ user.name|upper }} (Active)
{% endif %}
{% endfor %}
{% endif %}
""".strip()
    context4 = {
        "show_list": True,
        "users": [
            {"name": "alice", "active": True},
            {"name": "bob", "active": False},
            {"name": "carol", "active": True}
        ]
    }
    result4 = engine.render(template4, context4)
    print(f"Template:\n{template4}")
    print(f"Context: {context4}")
    print(f"Result:\n{result4}")
    print()
    
    # Example 5: Error handling
    try:
        bad_template = "{% if x %}unclosed"
        engine.render(bad_template, {})
    except TemplateSyntaxError as e:
        print(f"✓ Caught expected error: {e}")


if __name__ == "__main__":
    main()
