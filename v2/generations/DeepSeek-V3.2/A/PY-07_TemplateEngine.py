import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Custom exceptions
class TemplateSyntaxError(Exception):
    """Raised when a template has invalid syntax."""
    pass

class TemplateRenderError(Exception):
    """Raised when template rendering fails."""
    pass

# Token types for parsing
class TokenType(Enum):
    TEXT = "TEXT"
    VARIABLE = "VARIABLE"
    IF_START = "IF_START"
    IF_END = "IF_END"
    FOR_START = "FOR_START"
    FOR_END = "FOR_END"
    FILTER = "FILTER"

@dataclass
class Token:
    type: TokenType
    value: str
    start_pos: int
    end_pos: int

# Filter functions
class TemplateFilters:
    """Built-in template filters."""
    
    @staticmethod
    def upper(value: Any) -> str:
        return str(value).upper()
    
    @staticmethod
    def lower(value: Any) -> str:
        return str(value).lower()
    
    @staticmethod
    def title(value: Any) -> str:
        return str(value).title()
    
    @staticmethod
    def capitalize(value: Any) -> str:
        return str(value).capitalize()
    
    @staticmethod
    def length(value: Any) -> int:
        if hasattr(value, '__len__'):
            return len(value)
        return 0
    
    @staticmethod
    def default(value: Any, default_value: str = "") -> str:
        return str(value) if value not in (None, "", []) else default_value
    
    @staticmethod
    def join(value: List, delimiter: str = ", ") -> str:
        return delimiter.join(str(item) for item in value)
    
    @staticmethod
    def first(value: List) -> Any:
        return value[0] if value else ""
    
    @staticmethod
    def last(value: List) -> Any:
        return value[-1] if value else ""

# Template parser
class TemplateParser:
    """Parser for template syntax."""
    
    # Regex patterns
    VARIABLE_PATTERN = r'\{\{\s*([^}]+?)\s*\}\}'
    IF_START_PATTERN = r'\{%\s*if\s+([^%]+?)\s*%\}'
    IF_END_PATTERN = r'\{%\s*endif\s*%\}'
    FOR_START_PATTERN = r'\{%\s*for\s+([^%]+?)\s*in\s+([^%]+?)\s*%\}'
    FOR_END_PATTERN = r'\{%\s*endfor\s*%\}'
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.current_pos = 0
        
    def tokenize(self, template: str) -> List[Token]:
        """Convert template string into tokens."""
        self.tokens = []
        self.current_pos = 0
        
        while self.current_pos < len(template):
            # Try to match each pattern in order
            matched = False
            
            # Check for IF start
            match = re.match(self.IF_START_PATTERN, template[self.current_pos:])
            if match:
                self._add_token(TokenType.IF_START, match.group(0), match.group(1))
                self.current_pos += len(match.group(0))
                matched = True
                continue
            
            # Check for IF end
            match = re.match(self.IF_END_PATTERN, template[self.current_pos:])
            if match:
                self._add_token(TokenType.IF_END, match.group(0))
                self.current_pos += len(match.group(0))
                matched = True
                continue
            
            # Check for FOR start
            match = re.match(self.FOR_START_PATTERN, template[self.current_pos:])
            if match:
                self._add_token(TokenType.FOR_START, match.group(0), f"{match.group(1)} in {match.group(2)}")
                self.current_pos += len(match.group(0))
                matched = True
                continue
            
            # Check for FOR end
            match = re.match(self.FOR_END_PATTERN, template[self.current_pos:])
            if match:
                self._add_token(TokenType.FOR_END, match.group(0))
                self.current_pos += len(match.group(0))
                matched = True
                continue
            
            # Check for VARIABLE
            match = re.match(self.VARIABLE_PATTERN, template[self.current_pos:])
            if match:
                self._add_token(TokenType.VARIABLE, match.group(0), match.group(1))
                self.current_pos += len(match.group(0))
                matched = True
                continue
            
            # If no special pattern matched, consume as text
            if not matched:
                # Find the next special tag
                next_special = self._find_next_special(template)
                if next_special is None:
                    # No more special tags, rest is text
                    text = template[self.current_pos:]
                    self._add_token(TokenType.TEXT, text)
                    self.current_pos += len(text)
                else:
                    # There's a special tag ahead
                    text = template[self.current_pos:next_special]
                    self._add_token(TokenType.TEXT, text)
                    self.current_pos += len(text)
        
        return self.tokens
    
    def _add_token(self, token_type: TokenType, raw_value: str, parsed_value: str = None):
        """Add a token to the list."""
        start_pos = self.current_pos
        end_pos = self.current_pos + len(raw_value)
        
        if parsed_value is None:
            parsed_value = raw_value
        
        token = Token(
            type=token_type,
            value=parsed_value,
            start_pos=start_pos,
            end_pos=end_pos
        )
        self.tokens.append(token)
    
    def _find_next_special(self, template: str) -> Optional[int]:
        """Find the position of the next special tag."""
        patterns = [
            (self.VARIABLE_PATTERN, '{{'),
            (self.IF_START_PATTERN, '{%'),
            (self.IF_END_PATTERN, '{%'),
            (self.FOR_START_PATTERN, '{%'),
            (self.FOR_END_PATTERN, '{%'),
        ]
        
        min_pos = None
        for pattern, prefix in patterns:
            pos = template.find(prefix, self.current_pos)
            if pos != -1 and (min_pos is None or pos < min_pos):
                min_pos = pos
        
        return min_pos

# AST nodes
class ASTNode:
    """Abstract base class for AST nodes."""
    pass

@dataclass
class TextNode(ASTNode):
    content: str

@dataclass
class VariableNode(ASTNode):
    expression: str
    filters: List[str] = None

@dataclass
class IfNode(ASTNode):
    condition: str
    true_branch: List[ASTNode]
    false_branch: List[ASTNode] = None

@dataclass
class ForNode(ASTNode):
    item_var: str
    iterable_expr: str
    body: List[ASTNode]

# Template compiler
class TemplateCompiler:
    """Compiles tokens into an AST."""
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.current_index = 0
        self.ast: List[ASTNode] = []
    
    def compile(self, tokens: List[Token]) -> List[ASTNode]:
        """Compile tokens into an AST."""
        self.tokens = tokens
        self.current_index = 0
        self.ast = []
        
        while self.current_index < len(self.tokens):
            token = self.tokens[self.current_index]
            
            if token.type == TokenType.TEXT:
                self.ast.append(TextNode(token.value))
                self.current_index += 1
            
            elif token.type == TokenType.VARIABLE:
                node = self._parse_variable(token.value)
                self.ast.append(node)
                self.current_index += 1
            
            elif token.type == TokenType.IF_START:
                node = self._parse_if_statement()
                self.ast.append(node)
            
            elif token.type == TokenType.FOR_START:
                node = self._parse_for_loop()
                self.ast.append(node)
            
            elif token.type in (TokenType.IF_END, TokenType.FOR_END):
                raise TemplateSyntaxError(f"Unexpected end tag at position {token.start_pos}")
            
            else:
                raise TemplateSyntaxError(f"Unknown token type: {token.type}")
        
        return self.ast
    
    def _parse_variable(self, expression: str) -> VariableNode:
        """Parse a variable expression with filters."""
        # Split by pipe to separate variable from filters
        parts = [part.strip() for part in expression.split('|')]
        
        if not parts:
            raise TemplateSyntaxError(f"Empty variable expression")
        
        variable = parts[0]
        filters = parts[1:] if len(parts) > 1 else None
        
        return VariableNode(variable, filters)
    
    def _parse_if_statement(self) -> IfNode:
        """Parse an if statement."""
        start_token = self.tokens[self.current_index]
        if start_token.type != TokenType.IF_START:
            raise TemplateSyntaxError(f"Expected IF_START, got {start_token.type}")
        
        self.current_index += 1
        condition = start_token.value
        
        # Parse true branch
        true_branch = []
        false_branch = None
        
        while self.current_index < len(self.tokens):
            token = self.tokens[self.current_index]
            
            if token.type == TokenType.IF_END:
                self.current_index += 1
                break
            
            elif token.type == TokenType.IF_START:
                # Nested if
                node = self._parse_if_statement()
                true_branch.append(node)
            
            elif token.type == TokenType.FOR_START:
                # Nested for
                node = self._parse_for_loop()
                true_branch.append(node)
            
            elif token.type == TokenType.TEXT:
                true_branch.append(TextNode(token.value))
                self.current_index += 1
            
            elif token.type == TokenType.VARIABLE:
                node = self._parse_variable(token.value)
                true_branch.append(node)
                self.current_index += 1
            
            else:
                # Check for else (not implemented in this simple version)
                # For simplicity, we'll just consume tokens until endif
                self.current_index += 1
        
        else:
            # Reached end of tokens without finding endif
            raise TemplateSyntaxError(f"Unclosed if statement starting at position {start_token.start_pos}")
        
        return IfNode(condition, true_branch, false_branch)
    
    def _parse_for_loop(self) -> ForNode:
        """Parse a for loop."""
        start_token = self.tokens[self.current_index]
        if start_token.type != TokenType.FOR_START:
            raise TemplateSyntaxError(f"Expected FOR_START, got {start_token.type}")
        
        self.current_index += 1
        
        # Parse "item in iterable" pattern
        pattern = r'^\s*(\w+)\s+in\s+(.+)$'
        match = re.match(pattern, start_token.value)
        if not match:
            raise TemplateSyntaxError(f"Invalid for loop syntax: {start_token.value}")
        
        item_var = match.group(1)
        iterable_expr = match.group(2)
        
        # Parse loop body
        body = []
        
        while self.current_index < len(self.tokens):
            token = self.tokens[self.current_index]
            
            if token.type == TokenType.FOR_END:
                self.current_index += 1
                break
            
            elif token.type == TokenType.IF_START:
                # Nested if
                node = self._parse_if_statement()
                body.append(node)
            
            elif token.type == TokenType.FOR_START:
                # Nested for
                node = self._parse_for_loop()
                body.append(node)
            
            elif token.type == TokenType.TEXT:
                body.append(TextNode(token.value))
                self.current_index += 1
            
            elif token.type == TokenType.VARIABLE:
                node = self._parse_variable(token.value)
                body.append(node)
                self.current_index += 1
            
            else:
                # Check for else (not implemented in this simple version)
                self.current_index += 1
        
        else:
            # Reached end of tokens without finding endfor
            raise TemplateSyntaxError(f"Unclosed for loop starting at position {start_token.start_pos}")
        
        return ForNode(item_var, iterable_expr, body)

# Template engine
class TemplateEngine:
    """Main template engine class."""
    
    def __init__(self):
        self.parser = TemplateParser()
        self.compiler = TemplateCompiler()
        self.filters = TemplateFilters()
    
    def render(self, template_string: str, context: Dict) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_string: The template to render
            context: Dictionary of variables to use in the template
            
        Returns:
            Rendered string
            
        Raises:
            TemplateSyntaxError: If the template has invalid syntax
            TemplateRenderError: If rendering fails
        """
        try:
            # Tokenize
            tokens = self.parser.tokenize(template_string)
            
            # Compile to AST
            ast = self.compiler.compile(tokens)
            
            # Render
            result = self._render_ast(ast, context)
            return result
            
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise TemplateRenderError(f"Rendering failed: {str(e)}")
    
    def _render_ast(self, ast: List[ASTNode], context: Dict, loop_context: Dict = None) -> str:
        """Render an AST node."""
        result_parts = []
        
        for node in ast:
            if isinstance(node, TextNode):
                result_parts.append(node.content)
            
            elif isinstance(node, VariableNode):
                value = self._evaluate_expression(node.expression, context, loop_context)
                value = self._apply_filters(value, node.filters)
                result_parts.append(str(value))
            
            elif isinstance(node, IfNode):
                condition = self._evaluate_condition(node.condition, context, loop_context)
                if condition:
                    result_parts.append(self._render_ast(node.true_branch, context, loop_context))
                elif node.false_branch:
                    result_parts.append(self._render_ast(node.false_branch, context, loop_context))
            
            elif isinstance(node, ForNode):
                iterable = self._evaluate_expression(node.iterable_expr, context, loop_context)
                
                if not hasattr(iterable, '__iter__'):
                    raise TemplateRenderError(f"'{node.iterable_expr}' is not iterable")
                
                for item in iterable:
                    # Create new loop context
                    new_loop_context = {
                        **(loop_context or {}),
                        node.item_var: item
                    }
                    result_parts.append(self._render_ast(node.body, context, new_loop_context))
            
            else:
                raise TemplateRenderError(f"Unknown AST node type: {type(node)}")
        
        return ''.join(result_parts)
    
    def _evaluate_expression(self, expression: str, context: Dict, loop_context: Dict = None) -> Any:
        """Evaluate a variable expression."""
        # Combine context and loop context
        eval_context = {**(context or {}), **(loop_context or {})}
        
        # Split by dots for nested attribute access
        parts = expression.split('.')
        
        current_value = eval_context.get(parts[0])
        
        if current_value is None:
            # Try to find in parent contexts
            if loop_context and parts[0] in loop_context:
                current_value = loop_context[parts[0]]
            elif parts[0] not in eval_context:
                return ""
        
        # Traverse nested attributes
        for part in parts[1:]:
            if current_value is None:
                break
            
            if isinstance(current_value, dict):
                current_value = current_value.get(part)
            elif hasattr(current_value, part):
                current_value = getattr(current_value, part)
            else:
                current_value = None
        
        return current_value
    
    def _evaluate_condition(self, condition: str, context: Dict, loop_context: Dict = None) -> bool:
        """Evaluate a condition expression."""
        # Simple condition evaluation
        # For now, just check if the variable exists and is truthy
        expression = condition.strip()
        
        # Handle comparisons (simple cases)
        comparisons = ['==', '!=', '>', '<', '>=', '<=']
        for op in comparisons:
            if op in expression:
                left, right = expression.split(op, 1)
                left_val = self._evaluate_expression(left.strip(), context, loop_context)
                right_val = self._evaluate_expression(right.strip(), context, loop_context)
                
                # Try to convert to appropriate types
                try:
                    if '.' in str(left_val) or '.' in str(right_val):
                        left_val = float(left_val) if left_val is not None else 0
                        right_val = float(right_val) if right_val is not None else 0
                    else:
                        left_val = int(left_val) if left_val is not None else 0
                        right_val = int(right_val) if right_val is not None else 0
                except (ValueError, TypeError):
                    # Fall back to string comparison
                    left_val = str(left_val) if left_val is not None else ""
                    right_val = str(right_val) if right_val is not None else ""
                
                if op == '==':
                    return left_val == right_val
                elif op == '!=':
                    return left_val != right_val
                elif op == '>':
                    return left_val > right_val
                elif op == '<':
                    return left_val < right_val
                elif op == '>=':
                    return left_val >= right_val
                elif op == '<=':
                    return left_val <= right_val
        
        # Simple truthiness check
        value = self._evaluate_expression(expression, context, loop_context)
        return bool(value)
    
    def _apply_filters(self, value: Any, filters: List[str]) -> Any:
        """Apply filters to a value."""
        if not filters:
            return value
        
        current_value = value
        
        for filter_expr in filters:
            # Parse filter name and arguments
            if '(' in filter_expr and filter_expr.endswith(')'):
                # Filter with arguments
                filter_name, args_str = filter_expr[:-1].split('(', 1)
                filter_name = filter_name.strip()
                
                # Parse arguments (simple comma-separated)
                args = []
                for arg in args_str.split(','):
                    arg = arg.strip()
                    # Remove quotes if present
                    if (arg.startswith('"') and arg.endswith('"')) or \
                       (arg.startswith("'") and arg.endswith("'")):
                        arg = arg[1:-1]
                    args.append(arg)
            else:
                # Filter without arguments
                filter_name = filter_expr.strip()
                args = []
            
            # Get filter function
            filter_func = getattr(self.filters, filter_name, None)
            if not filter_func:
                raise TemplateRenderError(f"Unknown filter: {filter_name}")
            
            # Apply filter
            try:
                if args:
                    current_value = filter_func(current_value, *args)
                else:
                    current_value = filter_func(current_value)
            except Exception as e:
                raise TemplateRenderError(f"Filter '{filter_name}' failed: {str(e)}")
        
        return current_value

# Example usage
def main():
    """Example usage of the template engine."""
    print("Template Engine Example")
    print("=" * 60)
    
    # Create template engine
    engine = TemplateEngine()
    
    # Example 1: Simple variable substitution
    print("\n1. Simple Variable Substitution:")
    template1 = "Hello, {{ name }}! Welcome to {{ city }}."
    context1 = {"name": "Alice", "city": "New York"}
    result1 = engine.render(template1, context1)
    print(f"   Template: {template1}")
    print(f"   Context: {context1}")
    print(f"   Result: {result1}")
    
    # Example 2: Variable with filters
    print("\n2. Variable with Filters:")
    template2 = "Name: {{ name|upper }}, Lower: {{ name|lower }}, Title: {{ name|title }}"
    context2 = {"name": "john doe"}
    result2 = engine.render(template2, context2)
    print(f"   Template: {template2}")
    print(f"   Context: {context2}")
    print(f"   Result: {result2}")
    
    # Example 3: If statement
    print("\n3. If Statement:")
    template3 = """
{% if user.is_admin %}
    Welcome, Admin {{ user.name }}!
{% endif %}
{% if user.points > 100 %}
    You have {{ user.points }} points (Gold member)
{% endif %}
"""
    context3 = {
        "user": {
            "name": "Bob",
            "is_admin": True,
            "points": 150
        }
    }
    result3 = engine.render(template3, context3).strip()
    print(f"   Template: {template3}")
    print(f"   Context: {context3}")
    print(f"   Result:\n{result3}")
    
    # Example 4: For loop
    print("\n4. For Loop:")
    template4 = """
<ul>
{% for item in items %}
    <li>{{ item.name|upper }} - ${{ item.price }}</li>
{% endfor %}
</ul>
"""
    context4 = {
        "items": [
            {"name": "Apple", "price": 1.99},
            {"name": "Banana", "price": 0.99},
            {"name": "Orange", "price": 2.49}
        ]
    }
    result4 = engine.render(template4, context4).strip()
    print(f"   Template: {template4}")
    print(f"   Context: {context4}")
    print(f"   Result:\n{result4}")
    
    # Example 5: Nested blocks
    print("\n5. Nested Blocks (if inside for):")
    template5 = """
{% for user in users %}
    {% if user.active %}
        * {{ user.name }} (Active)
    {% else %}
        * {{ user.name }} (Inactive)
    {% endif %}
{% endfor %}
"""
    context5 = {
        "users": [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Charlie", "active": True}
        ]
    }
    result5 = engine.render(template5, context5).strip()
    print(f"   Template: {template5}")
    print(f"   Context: {context5}")
    print(f"   Result:\n{result5}")
    
    # Example 6: Complex example
    print("\n6. Complex Example:")
    template6 = """
# Report for {{ company.name|upper }}

## Summary
Total employees: {{ employees|length }}
Active projects: {{ projects|length }}

## Projects
{% for project in projects %}
### {{ project.name|title }}
Status: {% if project.completed %}Completed{% else %}In Progress{% endif %}
Team: {{ project.team|join:", " }}
Budget: ${{ project.budget|default:"Not specified" }}

{% endfor %}
"""
    context6 = {
        "company": {"name": "TechCorp Inc."},
        "employees": ["Alice", "Bob", "Charlie", "Diana"],
        "projects": [
            {
                "name": "website redesign",
                "completed": True,
                "team": ["Alice", "Bob"],
                "budget": 50000
            },
            {
                "name": "mobile app",
                "completed": False,
                "team": ["Charlie", "Diana"],
                "budget": None
            }
        ]
    }
    result6 = engine.render(template6, context6).strip()
    print(f"   Template: {template6}")
    print(f"   Context: {context6}")
    print(f"   Result:\n{result6}")
    
    # Example 7: Error handling
    print("\n7. Error Handling:")
    try:
        template7 = "{{ user.name|unknown_filter }}"
        context7 = {"user": {"name": "Test"}}
        result7 = engine.render(template7, context7)
    except TemplateRenderError as e:
        print(f"   Error (expected): {e}")
    
    try:
        template8 = "{% if user.name %}{% endif"  # Missing endif
        context8 = {"user": {"name": "Test"}}
        result8 = engine.render(template8, context8)
    except TemplateSyntaxError as e:
        print(f"   Error (expected): {e}")
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")

if __name__ == "__main__":
    main()