import re
from typing import Any


class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        super().__init__(f"TemplateSyntaxError at line {line}: {message}")


class TemplateEngine:
    """Simple template engine supporting variable substitution, if/for blocks, and filters.

    Supported syntax:
        {{ variable }}            - Variable substitution
        {{ variable|filter }}     - Variable with filter
        {% if condition %}...{% endif %}       - Conditional block
        {% for item in list %}...{% endfor %}  - Loop block
        Nested blocks supported.

    Built-in filters: upper, lower, title, length, default
    """

    FILTERS = {
        "upper": lambda v: str(v).upper(),
        "lower": lambda v: str(v).lower(),
        "title": lambda v: str(v).title(),
        "length": lambda v: str(len(v)),
        "strip": lambda v: str(v).strip(),
        "default": lambda v, d="": v if v is not None and v != "" else d,
    }

    def __init__(self):
        pass

    def apply_filter(self, value: Any, filter_name: str, filter_arg: str = "") -> str:
        """Apply a named filter to a value."""
        fn = self.FILTERS.get(filter_name)
        if fn is None:
            raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")

        if filter_arg:
            return fn(value, filter_arg)
        return fn(value)

    def resolve_variable(self, name: str, context: dict) -> Any:
        """Resolve a dotted variable name against the context."""
        parts = name.strip().split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            if value is None:
                return None
        return value

    def render_expression(self, expr: str, context: dict) -> str:
        """Render a single expression like 'user.name|upper'."""
        expr = expr.strip()

        # Check for filter
        parts = expr.split("|", 1)
        var_name = parts[0].strip()
        value = self.resolve_variable(var_name, context)

        if len(parts) > 1:
            filter_spec = parts[1].strip()
            # Handle filter with argument: default:value
            filter_parts = filter_spec.split(":", 1)
            filter_name = filter_parts[0].strip()
            filter_arg = filter_parts[1].strip() if len(filter_parts) > 1 else ""
            value = self.apply_filter(value, filter_name, filter_arg)

        if value is None:
            return ""
        return str(value)

    def evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a simple condition expression."""
        condition = condition.strip()

        # Handle negation
        if condition.startswith("not "):
            return not self.evaluate_condition(condition[4:], context)

        # Handle 'in' operator
        match = re.match(r'^(.+?)\s+in\s+(.+)$', condition)
        if match:
            left = self.resolve_variable(match.group(1).strip(), context)
            right = self.resolve_variable(match.group(2).strip(), context)
            if isinstance(right, (list, tuple, set, str)):
                return left in right
            return False

        # Handle equality
        for op in ("==", "!="):
            if op in condition:
                left_str, right_str = condition.split(op, 1)
                left = self.resolve_variable(left_str.strip(), context)
                # Try as literal first
                right = right_str.strip().strip("\"'")
                try:
                    right = type(left)(right) if left is not None else right
                except (ValueError, TypeError):
                    pass
                if op == "==":
                    return left == right
                else:
                    return left != right

        # Simple truthiness check
        value = self.resolve_variable(condition, context)
        return bool(value)

    def render(self, template: str, context: dict) -> str:
        """Render a template string with the given context."""
        tokens = self._tokenize(template)
        return self._render_tokens(tokens, context)

    def _tokenize(self, template: str) -> list:
        """Tokenize template into a list of (type, content) tuples."""
        tokens = []
        pos = 0

        while pos < len(template):
            # Look for {{ or {%
            next_expr = template.find("{{", pos)
            next_tag = template.find("{%", pos)

            if next_expr == -1 and next_tag == -1:
                tokens.append(("text", template[pos:]))
                break

            # Find the earliest one
            next_pos = len(template)
            if next_expr != -1:
                next_pos = min(next_pos, next_expr)
            if next_tag != -1:
                next_pos = min(next_pos, next_tag)

            # Add text before the tag
            if next_pos > pos:
                tokens.append(("text", template[pos:next_pos]))

            if template[next_pos:next_pos + 2] == "{{":
                # Variable expression
                end = template.find("}}", next_pos)
                if end == -1:
                    raise TemplateSyntaxError("Unclosed variable expression {{ }}")
                expr = template[next_pos + 2:end].strip()
                tokens.append(("var", expr))
                pos = end + 2
            else:
                # Control tag
                end = template.find("%}", next_pos)
                if end == -1:
                    raise TemplateSyntaxError("Unclosed control tag {% %}")
                tag_content = template[next_pos + 2:end].strip()
                tokens.append(("tag", tag_content))
                pos = end + 2

        return tokens

    def _render_tokens(self, tokens: list, context: dict) -> str:
        """Render a list of tokens into a string."""
        output = []
        i = 0

        while i < len(tokens):
            tok_type, tok_content = tokens[i]

            if tok_type == "text":
                output.append(tok_content)
                i += 1

            elif tok_type == "var":
                output.append(self.render_expression(tok_content, context))
                i += 1

            elif tok_type == "tag":
                tag = tok_content

                # If block
                if tag.startswith("if "):
                    condition = tag[3:]
                    # Find matching endif
                    body_tokens, else_tokens, end_i = self._find_if_block(tokens, i)
                    if self.evaluate_condition(condition, context):
                        output.append(self._render_tokens(body_tokens, context))
                    elif else_tokens:
                        output.append(self._render_tokens(else_tokens, context))
                    i = end_i + 1

                # For block
                elif tag.startswith("for "):
                    for_match = re.match(r'for\s+(\w+)\s+in\s+(.+)', tag)
                    if not for_match:
                        raise TemplateSyntaxError(f"Invalid for syntax: '{tag}'")
                    var_name = for_match.group(1)
                    iter_expr = for_match.group(2)
                    body_tokens, end_i = self._find_block_end(tokens, i, "for", "endfor")

                    iterable = self.resolve_variable(iter_expr.strip(), context)
                    if iterable is None:
                        raise TemplateSyntaxError(f"Variable '{iter_expr.strip()}' is None")
                    if not isinstance(iterable, (list, tuple)):
                        raise TemplateSyntaxError(f"'{iter_expr.strip()}' is not iterable")

                    for item in iterable:
                        loop_context = {**context, var_name: item}
                        output.append(self._render_tokens(body_tokens, loop_context))

                    i = end_i + 1

                else:
                    i += 1
            else:
                i += 1

        return "".join(output)

    def _find_block_end(self, tokens: list, start: int, open_tag: str, close_tag: str) -> tuple:
        """Find the matching endfor tag, handling nesting."""
        depth = 1
        body_tokens = []
        i = start + 1

        while i < len(tokens):
            tok_type, tok_content = tokens[i]
            if tok_type == "tag":
                if tok_content.startswith(open_tag + " "):
                    depth += 1
                elif tok_content == close_tag:
                    depth -= 1
                    if depth == 0:
                        return body_tokens, i
            body_tokens.append(tokens[i])
            i += 1

        raise TemplateSyntaxError(f"Unclosed {open_tag} block (missing {close_tag})")

    def _find_if_block(self, tokens: list, start: int) -> tuple:
        """Find matching endif/else, handling nested ifs."""
        depth = 1
        body_tokens = []
        else_tokens = []
        in_else = False
        i = start + 1

        while i < len(tokens):
            tok_type, tok_content = tokens[i]

            if tok_type == "tag":
                if tok_content.startswith("if "):
                    depth += 1
                    if in_else:
                        else_tokens.append(tokens[i])
                    else:
                        body_tokens.append(tokens[i])
                elif tok_content == "endif":
                    depth -= 1
                    if depth == 0:
                        return body_tokens, else_tokens, i
                    if in_else:
                        else_tokens.append(tokens[i])
                    else:
                        body_tokens.append(tokens[i])
                elif tok_content == "else" and depth == 1:
                    in_else = True
                else:
                    if in_else:
                        else_tokens.append(tokens[i])
                    else:
                        body_tokens.append(tokens[i])
            else:
                if in_else:
                    else_tokens.append(tokens[i])
                else:
                    body_tokens.append(tokens[i])

            i += 1

        raise TemplateSyntaxError("Unclosed if block (missing endif)")


def render(template: str, context: dict) -> str:
    """Convenience function to render a template."""
    engine = TemplateEngine()
    return engine.render(template, context)


if __name__ == "__main__":
    engine = TemplateEngine()

    # Basic variable substitution
    print("=== Variables ===")
    print(engine.render("Hello, {{ name }}!", {"name": "World"}))
    print(engine.render("{{ user.name|upper }} is {{ user.age }}", {"user": {"name": "alice", "age": 30}}))

    # Filters
    print("\n=== Filters ===")
    print(engine.render("{{ name|title }}", {"name": "john doe"}))
    print(engine.render("{{ items|length }}", {"items": [1, 2, 3]}))
    print(engine.render("{{ missing|default:N/A }}", {"missing": None}))

    # If/else
    print("\n=== If/Else ===")
    print(engine.render("{% if show %}Visible!{% endif %}", {"show": True}))
    print(engine.render("{% if show %}Visible!{% else %}Hidden!{% endif %}", {"show": False}))

    # For loop
    print("\n=== For Loop ===")
    print(engine.render("{% for item in items %}- {{ item }}\n{% endfor %}", {"items": ["a", "b", "c"]}))

    # Nested
    print("\n=== Nested ===")
    tpl = "{% for user in users %}{{ user.name|title }}: {% if user.active %}Active{% else %}Inactive{% endif %}\n{% endfor %}"
    ctx = {
        "users": [
            {"name": "alice", "active": True},
            {"name": "bob", "active": False},
            {"name": "charlie", "active": True},
        ]
    }
    print(engine.render(tpl, ctx))
