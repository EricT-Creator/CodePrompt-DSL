import re
from typing import Dict, Any, List


class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""
    pass


class TemplateEngine:
    def __init__(self):
        self.filters = {
            'upper': lambda x: str(x).upper(),
            'lower': lambda x: str(x).lower(),
            'title': lambda x: str(x).title(),
        }

    def _apply_filter(self, value: Any, filter_name: str) -> str:
        if filter_name in self.filters:
            return self.filters[filter_name](value)
        return str(value)

    def _parse_variable(self, var_expr: str, context: Dict[str, Any]) -> str:
        parts = var_expr.split('|')
        var_name = parts[0].strip()
        filter_name = parts[1].strip() if len(parts) > 1 else None

        keys = var_name.split('.')
        value = context
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                value = ''
                break

        if filter_name:
            value = self._apply_filter(value, filter_name)

        return str(value)

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        condition = condition.strip()

        # Handle 'not' operator
        if condition.startswith('not '):
            return not self._evaluate_condition(condition[4:], context)

        # Handle 'and' and 'or' operators
        if ' and ' in condition:
            parts = condition.split(' and ')
            return all(self._evaluate_condition(p, context) for p in parts)
        if ' or ' in condition:
            parts = condition.split(' or ')
            return any(self._evaluate_condition(p, context) for p in parts)

        # Handle comparisons
        match = re.match(r'(.+?)\s*(==|!=|<=|>=|<|>)\s*(.+)', condition)
        if match:
            left, op, right = match.groups()
            left_val = self._get_value(left.strip(), context)
            right_val = self._get_value(right.strip(), context)

            # Try to convert to numbers
            try:
                left_val = float(left_val)
                right_val = float(right_val)
            except (ValueError, TypeError):
                left_val = str(left_val)
                right_val = str(right_val)

            if op == '==':
                return left_val == right_val
            elif op == '!=':
                return left_val != right_val
            elif op == '<':
                return left_val < right_val
            elif op == '>':
                return left_val > right_val
            elif op == '<=':
                return left_val <= right_val
            elif op == '>=':
                return left_val >= right_val

        # Simple truthiness check
        value = self._get_value(condition, context)
        return bool(value) and value != 'False' and value != '0' and value != ''

    def _get_value(self, expr: str, context: Dict[str, Any]) -> Any:
        expr = expr.strip()

        # String literal
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Number literal
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Variable lookup
        keys = expr.split('.')
        value = context
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    value = ''
                    break
            else:
                value = ''
                break

        return value

    def _tokenize(self, template: str) -> List[tuple]:
        tokens = []
        pos = 0

        while pos < len(template):
            # Look for template tags
            var_match = re.search(r'\{\{\s*(.+?)\s*\}\}', template[pos:])
            tag_match = re.search(r'\{%\s*(.+?)\s*%\}', template[pos:])

            if not var_match and not tag_match:
                tokens.append(('text', template[pos:]))
                break

            var_pos = var_match.start() + pos if var_match else float('inf')
            tag_pos = tag_match.start() + pos if tag_match else float('inf')

            if var_pos < tag_pos:
                if var_pos > pos:
                    tokens.append(('text', template[pos:var_pos]))
                tokens.append(('var', var_match.group(1).strip()))
                pos = var_pos + len(var_match.group(0))
            else:
                if tag_pos > pos:
                    tokens.append(('text', template[pos:tag_pos]))
                tokens.append(('tag', tag_match.group(1).strip()))
                pos = tag_pos + len(tag_match.group(0))

        return tokens

    def _parse_blocks(self, tokens: List[tuple]) -> List[dict]:
        blocks = []
        i = 0

        while i < len(tokens):
            token_type, content = tokens[i]

            if token_type == 'text':
                blocks.append({'type': 'text', 'content': content})
                i += 1

            elif token_type == 'var':
                blocks.append({'type': 'var', 'expr': content})
                i += 1

            elif token_type == 'tag':
                if content.startswith('if '):
                    condition = content[3:].strip()
                    if_body = []
                    else_body = None
                    i += 1

                    if_depth = 1
                    while i < len(tokens) and if_depth > 0:
                        t_type, t_content = tokens[i]
                        if t_type == 'tag':
                            if t_content.startswith('if '):
                                if_depth += 1
                            elif t_content == 'endif':
                                if_depth -= 1
                                if if_depth == 0:
                                    i += 1
                                    break
                            elif t_content.startswith('else') and if_depth == 1:
                                else_body = []
                                i += 1
                                continue

                        if else_body is not None and if_depth == 1:
                            else_body.append(tokens[i])
                        else:
                            if_body.append(tokens[i])
                        i += 1

                    if if_depth > 0:
                        raise TemplateSyntaxError("Unclosed if block")

                    blocks.append({
                        'type': 'if',
                        'condition': condition,
                        'if_body': self._parse_blocks(if_body),
                        'else_body': self._parse_blocks(else_body) if else_body else None
                    })

                elif content.startswith('for '):
                    match = re.match(r'for\s+(\w+)\s+in\s+(.+)', content)
                    if not match:
                        raise TemplateSyntaxError(f"Invalid for syntax: {content}")

                    var_name, iterable_expr = match.groups()
                    for_body = []
                    i += 1

                    for_depth = 1
                    while i < len(tokens) and for_depth > 0:
                        t_type, t_content = tokens[i]
                        if t_type == 'tag':
                            if t_content.startswith('for '):
                                for_depth += 1
                            elif t_content == 'endfor':
                                for_depth -= 1
                                if for_depth == 0:
                                    i += 1
                                    break

                        for_body.append(tokens[i])
                        i += 1

                    if for_depth > 0:
                        raise TemplateSyntaxError("Unclosed for block")

                    blocks.append({
                        'type': 'for',
                        'var_name': var_name,
                        'iterable': iterable_expr.strip(),
                        'body': self._parse_blocks(for_body)
                    })

                elif content in ('endif', 'else', 'endfor'):
                    raise TemplateSyntaxError(f"Unexpected tag: {content}")

                else:
                    raise TemplateSyntaxError(f"Unknown tag: {content}")

        return blocks

    def _render_blocks(self, blocks: List[dict], context: Dict[str, Any]) -> str:
        result = []

        for block in blocks:
            if block['type'] == 'text':
                result.append(block['content'])

            elif block['type'] == 'var':
                result.append(self._parse_variable(block['expr'], context))

            elif block['type'] == 'if':
                condition_met = self._evaluate_condition(block['condition'], context)
                if condition_met:
                    result.append(self._render_blocks(block['if_body'], context))
                elif block['else_body']:
                    result.append(self._render_blocks(block['else_body'], context))

            elif block['type'] == 'for':
                iterable = self._get_value(block['iterable'], context)
                if not isinstance(iterable, (list, tuple)):
                    iterable = []

                for item in iterable:
                    new_context = dict(context)
                    new_context[block['var_name']] = item
                    result.append(self._render_blocks(block['body'], new_context))

        return ''.join(result)

    def render(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with the given context."""
        tokens = self._tokenize(template_string)
        blocks = self._parse_blocks(tokens)
        return self._render_blocks(blocks, context)


def render(template_string: str, context: Dict[str, Any]) -> str:
    """Convenience function to render a template."""
    engine = TemplateEngine()
    return engine.render(template_string, context)


if __name__ == "__main__":
    # Test cases
    engine = TemplateEngine()

    # Test 1: Variable substitution
    template1 = "Hello, {{name}}!"
    result1 = engine.render(template1, {"name": "World"})
    print(f"Test 1: {result1}")

    # Test 2: Filters
    template2 = "{{name|upper}}, {{name|lower}}, {{name|title}}"
    result2 = engine.render(template2, {"name": "hello world"})
    print(f"Test 2: {result2}")

    # Test 3: If condition
    template3 = "{% if user %}Hello, {{user}}!{% else %}Hello, Guest!{% endif %}"
    result3a = engine.render(template3, {"user": "Alice"})
    result3b = engine.render(template3, {})
    print(f"Test 3a: {result3a}")
    print(f"Test 3b: {result3b}")

    # Test 4: For loop
    template4 = "Items: {% for item in items %}{{item}}{% if not loop.last %}, {% endif %}{% endfor %}"
    result4 = engine.render(template4, {"items": ["a", "b", "c"]})
    print(f"Test 4: {result4}")

    # Test 5: Nested blocks
    template5 = """
{% if show_list %}
{% for item in items %}
{% if item.active %}
- {{item.name|upper}}
{% else %}
- {{item.name|lower}}
{% endif %}
{% endfor %}
{% else %}
No items to show
{% endif %}
""".strip()
    result5 = engine.render(template5, {
        "show_list": True,
        "items": [
            {"name": "Apple", "active": True},
            {"name": "Banana", "active": False}
        ]
    })
    print(f"Test 5:\n{result5}")
