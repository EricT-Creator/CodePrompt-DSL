import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass


class TemplateSyntaxError(Exception):
    """Exception raised for syntax errors in templates"""
    pass


@dataclass
class Token:
    """Represents a token in the template"""
    type: str  # 'text', 'var', 'if_start', 'if_end', 'for_start', 'for_end'
    value: str
    position: int


class TemplateEngine:
    """
    Simple template engine with support for:
    - Variable substitution: {{variable}}
    - If blocks: {% if condition %}...{% endif %}
    - For loops: {% for item in list %}...{% endfor %}
    - Filters: {{variable|upper|lower|title}}
    - Nested blocks
    """
    
    # Regex patterns
    VAR_PATTERN = r'\{\{\s*(\w+)(?:\s*\|\s*(\w+))*\s*\}\}'
    BLOCK_START_PATTERN = r'\{%\s*(\w+)(?:\s+(\w+)\s+(\w+))?\s*%\}'
    BLOCK_END_PATTERN = r'\{%\s*end(\w+)\s*%\}'
    
    # Supported filters
    FILTERS = {
        'upper': str.upper,
        'lower': str.lower,
        'title': str.title,
        'capitalize': str.capitalize,
        'strip': str.strip,
        'length': len,
        'reverse': lambda s: s[::-1],
    }
    
    def __init__(self):
        """Initialize template engine"""
        pass
    
    def _tokenize(self, template: str) -> List[Token]:
        """
        Tokenize template into text and control tokens.
        
        Args:
            template: Template string
        
        Returns:
            List of Token objects
        
        Raises:
            TemplateSyntaxError: If syntax is invalid
        """
        tokens = []
        pos = 0
        stack = []  # For tracking block nesting
        
        while pos < len(template):
            # Look for variable substitution
            var_match = re.search(self.VAR_PATTERN, template[pos:])
            
            # Look for block start
            block_start_match = re.search(self.BLOCK_START_PATTERN, template[pos:])
            
            # Look for block end
            block_end_match = re.search(self.BLOCK_END_PATTERN, template[pos:])
            
            # Find the earliest match
            matches = []
            if var_match:
                matches.append(('var', var_match))
            if block_start_match:
                matches.append(('block_start', block_start_match))
            if block_end_match:
                matches.append(('block_end', block_end_match))
            
            if not matches:
                # No more special tokens, add remaining text
                if pos < len(template):
                    tokens.append(Token('text', template[pos:], pos))
                break
            
            # Find the earliest match
            earliest = min(matches, key=lambda x: x[1].start())
            match_type, match = earliest
            match_start = pos + match.start()
            
            # Add text before the match
            if match_start > pos:
                tokens.append(Token('text', template[pos:match_start], pos))
            
            if match_type == 'var':
                # Variable token
                var_name = match.group(1)
                filters = match.group(2) if match.group(2) else ''
                tokens.append(Token('var', f"{var_name}|{filters}", match_start))
                pos = pos + match.end()
            
            elif match_type == 'block_start':
                # Block start token
                block_type = match.group(1)
                if block_type == 'if':
                    condition = match.group(2)
                    # Simple condition check (just variable name for now)
                    tokens.append(Token('if_start', condition, match_start))
                    stack.append('if')
                elif block_type == 'for':
                    item_var = match.group(2)
                    iterable_var = match.group(3)
                    tokens.append(Token('for_start', f"{item_var} {iterable_var}", match_start))
                    stack.append('for')
                else:
                    raise TemplateSyntaxError(f"Unknown block type: {block_type} at position {match_start}")
                
                pos = pos + match.end()
            
            elif match_type == 'block_end':
                # Block end token
                block_type = match.group(1)
                if not stack:
                    raise TemplateSyntaxError(f"Unexpected end{block_type} at position {match_start}")
                
                last_block = stack.pop()
                if last_block != block_type:
                    raise TemplateSyntaxError(
                        f"Mismatched blocks: expected end{last_block}, got end{block_type} at position {match_start}"
                    )
                
                tokens.append(Token(f"{block_type}_end", '', match_start))
                pos = pos + match.end()
        
        # Check for unclosed blocks
        if stack:
            raise TemplateSyntaxError(f"Unclosed block(s): {stack}")
        
        return tokens
    
    def _apply_filters(self, value: Any, filters_str: str) -> str:
        """
        Apply filters to a value.
        
        Args:
            value: Value to filter
            filters_str: Pipe-separated filter names (e.g., "upper|lower")
        
        Returns:
            Filtered string
        """
        if not filters_str:
            return str(value)
        
        filter_names = [f.strip() for f in filters_str.split('|') if f.strip()]
        result = value
        
        for filter_name in filter_names:
            if filter_name in self.FILTERS:
                result = self.FILTERS[filter_name](result)
            else:
                # Try to call as method if value has it
                if hasattr(result, filter_name) and callable(getattr(result, filter_name)):
                    result = getattr(result, filter_name)()
                else:
                    raise ValueError(f"Unknown filter: {filter_name}")
        
        return str(result)
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Evaluate a simple condition.
        
        Args:
            condition: Condition string (variable name)
            context: Template context
        
        Returns:
            True if condition is truthy, False otherwise
        """
        if condition in context:
            value = context[condition]
            # Simple truthiness check
            if isinstance(value, bool):
                return value
            elif isinstance(value, (int, float)):
                return value != 0
            elif isinstance(value, str):
                return bool(value.strip())
            elif isinstance(value, (list, tuple, dict, set)):
                return bool(value)
            else:
                return bool(value)
        return False
    
    def _render_tokens(self, tokens: List[Token], context: Dict) -> str:
        """
        Render tokens with context.
        
        Args:
            tokens: List of Token objects
            context: Template context
        
        Returns:
            Rendered string
        """
        result = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == 'text':
                result.append(token.value)
                i += 1
            
            elif token.type == 'var':
                # Parse variable name and filters
                parts = token.value.split('|', 1)
                var_name = parts[0]
                filters = parts[1] if len(parts) > 1 else ''
                
                if var_name in context:
                    value = context[var_name]
                    result.append(self._apply_filters(value, filters))
                else:
                    # Variable not found - leave placeholder
                    result.append(f"{{{{{var_name}}}}}")
                
                i += 1
            
            elif token.type == 'if_start':
                # Find matching endif
                if_end_idx = i + 1
                depth = 1
                
                while if_end_idx < len(tokens):
                    if tokens[if_end_idx].type == 'if_start':
                        depth += 1
                    elif tokens[if_end_idx].type == 'if_end':
                        depth -= 1
                        if depth == 0:
                            break
                    if_end_idx += 1
                
                if if_end_idx >= len(tokens):
                    raise TemplateSyntaxError("Unclosed if block")
                
                # Extract condition
                condition = token.value
                
                # Evaluate condition
                if self._evaluate_condition(condition, context):
                    # Render content inside if block
                    if_content = self._render_tokens(tokens[i+1:if_end_idx], context)
                    result.append(if_content)
                
                i = if_end_idx + 1
            
            elif token.type == 'for_start':
                # Find matching endfor
                for_end_idx = i + 1
                depth = 1
                
                while for_end_idx < len(tokens):
                    if tokens[for_end_idx].type == 'for_start':
                        depth += 1
                    elif tokens[for_end_idx].type == 'for_end':
                        depth -= 1
                        if depth == 0:
                            break
                    for_end_idx += 1
                
                if for_end_idx >= len(tokens):
                    raise TemplateSyntaxError("Unclosed for block")
                
                # Parse for loop parameters
                parts = token.value.split()
                if len(parts) != 2:
                    raise TemplateSyntaxError(f"Invalid for syntax: {token.value}")
                
                item_var, iterable_var = parts
                
                # Get iterable from context
                if iterable_var not in context:
                    raise ValueError(f"Iterable '{iterable_var}' not found in context")
                
                iterable = context[iterable_var]
                if not hasattr(iterable, '__iter__'):
                    raise TypeError(f"'{iterable_var}' is not iterable")
                
                # Render for loop content for each item
                for_content_tokens = tokens[i+1:for_end_idx]
                for item in iterable:
                    # Create new context with loop variable
                    loop_context = context.copy()
                    loop_context[item_var] = item
                    loop_context['loop'] = {
                        'index': 0,  # Would need to track index
                        'first': False,  # Simplified
                        'last': False,  # Simplified
                    }
                    
                    item_result = self._render_tokens(for_content_tokens, loop_context)
                    result.append(item_result)
                
                i = for_end_idx + 1
            
            else:
                # Skip block end tokens
                i += 1
        
        return ''.join(result)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with context.
        
        Args:
            template: Template string
            context: Dictionary of variables to use in template
        
        Returns:
            Rendered string
        
        Raises:
            TemplateSyntaxError: If template has syntax errors
        """
        # Tokenize template
        tokens = self._tokenize(template)
        
        # Render tokens with context
        result = self._render_tokens(tokens, context)
        
        return result
    
    def compile(self, template: str) -> callable:
        """
        Compile template into a function.
        
        Args:
            template: Template string
        
        Returns:
            Function that takes context and returns rendered string
        
        Raises:
            TemplateSyntaxError: If template has syntax errors
        """
        # Tokenize once
        tokens = self._tokenize(template)
        
        def render_function(context: Dict[str, Any]) -> str:
            return self._render_tokens(tokens, context)
        
        return render_function


# Example usage and testing
def main():
    """Example usage of TemplateEngine"""
    
    engine = TemplateEngine()
    
    print("=== Template Engine Examples ===")
    print()
    
    # Example 1: Simple variable substitution
    print("1. Simple variable substitution:")
    template1 = "Hello, {{name}}! Welcome to {{city}}."
    context1 = {'name': 'Alice', 'city': 'New York'}
    result1 = engine.render(template1, context1)
    print(f"   Template: {template1}")
    print(f"   Context: {context1}")
    print(f"   Result: {result1}")
    print()
    
    # Example 2: With filters
    print("2. Variable substitution with filters:")
    template2 = "Name: {{name|upper}}, Lowercase: {{name|lower}}, Title: {{name|title}}"
    context2 = {'name': 'john doe'}
    result2 = engine.render(template2, context2)
    print(f"   Template: {template2}")
    print(f"   Context: {context2}")
    print(f"   Result: {result2}")
    print()
    
    # Example 3: If block
    print("3. If block:")
    template3 = """
    {% if user_logged_in %}
        Welcome back, {{username}}!
    {% endif %}
    You have {{message_count}} new messages.
    """
    context3a = {'user_logged_in': True, 'username': 'Alice', 'message_count': 5}
    context3b = {'user_logged_in': False, 'message_count': 0}
    
    result3a = engine.render(template3, context3a)
    result3b = engine.render(template3, context3b)
    
    print(f"   Template: {template3.strip()}")
    print(f"   Context (logged in): {context3a}")
    print(f"   Result: {result3a.strip()}")
    print(f"   Context (not logged in): {context3b}")
    print(f"   Result: {result3b.strip()}")
    print()
    
    # Example 4: For loop
    print("4. For loop:")
    template4 = """
    Shopping List:
    {% for item in items %}
      - {{item|title}}
    {% endfor %}
    Total: {{items|length}} items
    """
    context4 = {'items': ['apples', 'bananas', 'milk', 'bread']}
    result4 = engine.render(template4, context4)
    print(f"   Template: {template4.strip()}")
    print(f"   Context: {context4}")
    print(f"   Result:\n{result4.strip()}")
    print()
    
    # Example 5: Nested blocks
    print("5. Nested blocks (if inside for):")
    template5 = """
    Users:
    {% for user in users %}
      {% if user.active %}
        * {{user.name|upper}} (Active)
      {% else %}
        * {{user.name}} (Inactive)
      {% endif %}
    {% endfor %}
    """
    context5 = {
        'users': [
            {'name': 'alice', 'active': True},
            {'name': 'bob', 'active': False},
            {'name': 'charlie', 'active': True},
        ]
    }
    result5 = engine.render(template5, context5)
    print(f"   Template: {template5.strip()}")
    print(f"   Context: {context5}")
    print(f"   Result:\n{result5.strip()}")
    print()
    
    # Example 6: Compile and reuse
    print("6. Compile template for reuse:")
    template6 = "Product: {{name}}, Price: ${{price}}, Discounted: ${{price|discount}}"
    
    # Add custom filter
    engine.FILTERS['discount'] = lambda price: round(price * 0.9, 2)
    
    compiled = engine.compile(template6)
    
    products = [
        {'name': 'Laptop', 'price': 999.99},
        {'name': 'Phone', 'price': 699.99},
        {'name': 'Tablet', 'price': 399.99},
    ]
    
    print(f"   Template: {template6}")
    for product in products:
        result = compiled(product)
        print(f"   Result: {result}")
    print()
    
    # Example 7: Error handling
    print("7. Error handling:")
    
    # Missing variable
    try:
        template7 = "Hello {{unknown}}!"
        result7 = engine.render(template7, {})
        print(f"   Missing variable: {result7}")
    except Exception as e:
        print(f"   Missing variable error: {e}")
    
    # Syntax error
    try:
        template8 = "{% if x %}No endif!"
        result8 = engine.render(template8, {'x': True})
    except TemplateSyntaxError as e:
        print(f"   Syntax error: {e}")
    
    # Invalid filter
    try:
        template9 = "{{name|unknown_filter}}"
        result9 = engine.render(template9, {'name': 'test'})
    except ValueError as e:
        print(f"   Invalid filter: {e}")
    
    print()
    print("=== Performance Test ===")
    
    # Test with larger template
    large_template = """
    Report for {{company}}:
    
    Departments:
    {% for dept in departments %}
    ## {{dept.name|upper}}
      Manager: {{dept.manager}}
      Employees: {{dept.employees|length}}
      {% if dept.budget > 100000 %}
      Budget: ${{dept.budget}} (Large)
      {% else %}
      Budget: ${{dept.budget}} (Small)
      {% endif %}
      
      Projects:
      {% for project in dept.projects %}
        - {{project.name}}: {{project.status|title}}
      {% endfor %}
      
    {% endfor %}
    
    Total Departments: {{departments|length}}
    """
    
    large_context = {
        'company': 'TechCorp',
        'departments': [
            {
                'name': 'engineering',
                'manager': 'Alice Smith',
                'employees': 50,
                'budget': 500000,
                'projects': [
                    {'name': 'Project Alpha', 'status': 'active'},
                    {'name': 'Project Beta', 'status': 'completed'},
                ]
            },
            {
                'name': 'marketing',
                'manager': 'Bob Johnson',
                'employees': 20,
                'budget': 80000,
                'projects': [
                    {'name': 'Campaign 2024', 'status': 'planning'},
                ]
            },
        ]
    }
    
    import time
    start = time.time()
    result = engine.render(large_template, large_context)
    elapsed = time.time() - start
    
    print(f"Large template rendered in {elapsed:.3f} seconds")
    print(f"Output length: {len(result)} characters")
    print("First 200 chars of output:")
    print(result[:200] + "...")


if __name__ == "__main__":
    main()