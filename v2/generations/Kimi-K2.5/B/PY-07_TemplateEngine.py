import re
from typing import Dict, Any, List


class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""
    pass


class TemplateEngine:
    """
    Simple template engine supporting:
    - {{var}} substitution
    - {% if condition %}...{% endif %}
    - {% for item in list %}...{% endfor %}
    - Filters: |upper, |lower, |title
    """
    
    def __init__(self):
        # Regex patterns for parsing
        self.token_pattern = re.compile(
            r'\{\{\s*(.+?)\s*\}\}|'  # {{ variable }}
            r'\{%\s*if\s+(.+?)\s*%\}|'  # {% if condition %}
            r'\{%\s*endif\s*%\}|'  # {% endif %}
            r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}|'  # {% for item in list %}
            r'\{%\s*endfor\s*%\}'  # {% endfor %}
        )
        
        self.filter_pattern = re.compile(r'^(\w+)\s*\|\s*(upper|lower|title)$')
        self.var_pattern = re.compile(r'^(\w+)$')
    
    def _apply_filter(self, value: Any, filter_name: str) -> str:
        """Apply a filter to a value."""
        value_str = str(value)
        if filter_name == 'upper':
            return value_str.upper()
        elif filter_name == 'lower':
            return value_str.lower()
        elif filter_name == 'title':
            return value_str.title()
        return value_str
    
    def _get_value(self, var_name: str, context: Dict[str, Any]) -> Any:
        """Get value from context, handling filters."""
        # Check for filter
        filter_match = self.filter_pattern.match(var_name)
        if filter_match:
            var = filter_match.group(1)
            filter_name = filter_match.group(2)
            value = context.get(var, '')
            return self._apply_filter(value, filter_name)
        
        # Simple variable
        var_match = self.var_pattern.match(var_name)
        if var_match:
            var = var_match.group(1)
            return context.get(var, '')
        
        return ''
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string."""
        condition = condition.strip()
        
        # Handle 'not' operator
        if condition.startswith('not '):
            return not self._evaluate_condition(condition[4:], context)
        
        # Handle comparisons
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = self._get_value(parts[0].strip(), context)
                    right = parts[1].strip()
                    
                    # Remove quotes from right side if present
                    if (right.startswith('"') and right.endswith('"')) or \
                       (right.startswith("'") and right.endswith("'")):
                        right = right[1:-1]
                    else:
                        # Try to get from context or convert to number
                        right = context.get(right, right)
                        try:
                            right = int(right)
                        except (ValueError, TypeError):
                            try:
                                right = float(right)
                            except (ValueError, TypeError):
                                pass
                    
                    try:
                        if op == '==':
                            return left == right
                        elif op == '!=':
                            return left != right
                        elif op == '>=':
                            return float(left) >= float(right)
                        elif op == '<=':
                            return float(left) <= float(right)
                        elif op == '>':
                            return float(left) > float(right)
                        elif op == '<':
                            return float(left) < float(right)
                    except (ValueError, TypeError):
                        return False
        
        # Simple truthiness check
        value = self._get_value(condition, context)
        return bool(value)
    
    def _tokenize(self, template: str) -> List[tuple]:
        """Tokenize template into structured components."""
        tokens = []
        pos = 0
        
        while pos < len(template):
            match = self.token_pattern.search(template, pos)
            
            if not match:
                # Add remaining text
                if pos < len(template):
                    tokens.append(('text', template[pos:]))
                break
            
            # Add text before match
            if match.start() > pos:
                tokens.append(('text', template[pos:match.start()]))
            
            # Determine token type
            if match.group(1):  # {{ variable }}
                tokens.append(('var', match.group(1).strip()))
            elif match.group(2):  # {% if condition %}
                tokens.append(('if_start', match.group(2).strip()))
            elif match.group(0).strip() == '{% endif %}':
                tokens.append(('if_end', ''))
            elif match.group(3) and match.group(4):  # {% for item in list %}
                tokens.append(('for_start', (match.group(3).strip(), match.group(4).strip())))
            elif match.group(0).strip() == '{% endfor %}':
                tokens.append(('for_end', ''))
            
            pos = match.end()
        
        return tokens
    
    def _parse(self, tokens: List[tuple], idx: int = 0) -> tuple:
        """Parse tokens into an AST-like structure."""
        result = []
        
        while idx < len(tokens):
            token_type, token_value = tokens[idx]
            
            if token_type == 'text':
                result.append(('text', token_value))
            elif token_type == 'var':
                result.append(('var', token_value))
            elif token_type == 'if_start':
                # Parse if block
                condition = token_value
                block_tokens, idx = self._parse(tokens, idx + 1)
                
                if idx >= len(tokens) or tokens[idx][0] != 'if_end':
                    raise TemplateSyntaxError("Missing {% endif %}")
                
                result.append(('if', condition, block_tokens))
            elif token_type == 'if_end':
                return result, idx
            elif token_type == 'for_start':
                # Parse for block
                var_name, list_name = token_value
                block_tokens, idx = self._parse(tokens, idx + 1)
                
                if idx >= len(tokens) or tokens[idx][0] != 'for_end':
                    raise TemplateSyntaxError("Missing {% endfor %}")
                
                result.append(('for', var_name, list_name, block_tokens))
            elif token_type == 'for_end':
                return result, idx
            
            idx += 1
        
        return result, idx
    
    def _render_node(self, node: tuple, context: Dict[str, Any]) -> str:
        """Render a single AST node."""
        node_type = node[0]
        
        if node_type == 'text':
            return node[1]
        elif node_type == 'var':
            return str(self._get_value(node[1], context))
        elif node_type == 'if':
            condition = node[1]
            block = node[2]
            
            if self._evaluate_condition(condition, context):
                return ''.join(self._render_node(n, context) for n in block)
            return ''
        elif node_type == 'for':
            var_name = node[1]
            list_name = node[2]
            block = node[3]
            
            items = context.get(list_name, [])
            if not isinstance(items, (list, tuple)):
                items = [items]
            
            result = []
            for item in items:
                new_context = dict(context)
                new_context[var_name] = item
                result.append(''.join(self._render_node(n, new_context) for n in block))
            
            return ''.join(result)
        
        return ''
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template: Template string
            context: Dictionary of variables
        
        Returns:
            Rendered string
        
        Raises:
            TemplateSyntaxError: If template syntax is invalid
        """
        tokens = self._tokenize(template)
        ast, _ = self._parse(tokens)
        return ''.join(self._render_node(node, context) for node in ast)


def main():
    """Example usage of TemplateEngine."""
    engine = TemplateEngine()
    
    # Example 1: Variable substitution
    template1 = "Hello, {{name}}!"
    result1 = engine.render(template1, {"name": "World"})
    print(f"Template: {template1}")
    print(f"Result:   {result1}\n")
    
    # Example 2: Filters
    template2 = "Hello, {{name|upper}}!"
    result2 = engine.render(template2, {"name": "world"})
    print(f"Template: {template2}")
    print(f"Result:   {result2}\n")
    
    # Example 3: If statement
    template3 = "{% if show_greeting %}Hello, {{name}}!{% endif %}"
    result3 = engine.render(template3, {"show_greeting": True, "name": "Alice"})
    print(f"Template: {template3}")
    print(f"Result:   {result3}\n")
    
    # Example 4: For loop
    template4 = "Items: {% for item in items %}{{item}}, {% endfor %}"
    result4 = engine.render(template4, {"items": ["apple", "banana", "cherry"]})
    print(f"Template: {template4}")
    print(f"Result:   {result4}\n")
    
    # Example 5: Nested blocks
    template5 = """
{% if user %}
Welcome, {{user.name|title}}!
Your items:
{% for item in user.items %}
  - {{item|upper}}
{% endfor %}
{% else %}
Please log in.
{% endif %}
""".strip()
    
    context5 = {
        "user": {
            "name": "john doe",
            "items": ["laptop", "phone", "tablet"]
        }
    }
    result5 = engine.render(template5, context5)
    print(f"Template:\n{template5}")
    print(f"\nResult:\n{result5}\n")


if __name__ == "__main__":
    main()
