import re
from typing import Any, Dict, List


class TemplateSyntaxError(Exception):
    """Raised when the template contains invalid syntax."""
    pass


class TemplateEngine:
    """A lightweight template engine supporting variable substitution,
    conditionals, loops, nested blocks, and filters.

    Syntax:
        {{ var }}              - variable substitution
        {{ var|upper }}        - filter pipe
        {% if cond %}...{% endif %}
        {% for item in list %}...{% endfor %}
    """

    FILTERS = {
        "upper": lambda v: str(v).upper(),
        "lower": lambda v: str(v).lower(),
        "title": lambda v: str(v).title(),
    }

    VAR_PATTERN = re.compile(r"\{\{(.+?)\}\}")
    BLOCK_PATTERN = re.compile(
        r"\{%\s*(if|for|endif|endfor)\s*(.*?)\s*%\}"
    )

    def __init__(self) -> None:
        pass

    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template string with the given context."""
        tree = self._parse(template)
        return self._execute(tree, context)

    def _parse(self, template: str) -> List:
        """Parse template into a tree of nodes."""
        tokens = self._tokenize(template)
        tree, remaining = self._parse_tokens(tokens, None)
        if remaining:
            tag = remaining[0]
            if tag[0] == "block":
                raise TemplateSyntaxError(f"Unexpected block tag: {tag[1]}")
        return tree

    def _tokenize(self, template: str) -> List:
        """Split template into text, variable, and block tokens."""
        tokens = []
        pos = 0
        combined = re.compile(
            r"(\{\{.+?\}\}|\{%\s*(?:if|for|endif|endfor)\s*.*?\s*%\})"
        )

        for match in combined.finditer(template):
            start, end = match.span()
            if start > pos:
                tokens.append(("text", template[pos:start]))

            tag = match.group()
            if tag.startswith("{{"):
                inner = tag[2:-2].strip()
                tokens.append(("var", inner))
            else:
                inner = tag[2:-2].strip()
                block_match = re.match(r"(if|for|endif|endfor)\s*(.*)", inner)
                if block_match:
                    tokens.append(("block", block_match.group(1), block_match.group(2).strip()))
                else:
                    raise TemplateSyntaxError(f"Invalid block tag: {tag}")
            pos = end

        if pos < len(template):
            tokens.append(("text", template[pos:]))

        return tokens

    def _parse_tokens(self, tokens: List, end_tag: str) -> tuple:
        """Recursively parse tokens into a nested tree structure."""
        nodes = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token[0] == "text":
                nodes.append(("text", token[1]))
                i += 1

            elif token[0] == "var":
                nodes.append(("var", token[1]))
                i += 1

            elif token[0] == "block":
                tag_type = token[1]

                if tag_type == "if":
                    condition = token[2]
                    if not condition:
                        raise TemplateSyntaxError("{% if %} requires a condition")
                    body, remaining = self._parse_tokens(tokens[i + 1:], "endif")
                    nodes.append(("if", condition, body))
                    i += 1 + (len(tokens) - i - 1 - len(remaining))
                    i = len(tokens) - len(remaining)

                elif tag_type == "for":
                    for_match = re.match(r"(\w+)\s+in\s+(\w+)", token[2])
                    if not for_match:
                        raise TemplateSyntaxError(
                            f"Invalid for syntax: '{token[2]}'. Expected 'item in list'"
                        )
                    var_name = for_match.group(1)
                    iter_name = for_match.group(2)
                    body, remaining = self._parse_tokens(tokens[i + 1:], "endfor")
                    nodes.append(("for", var_name, iter_name, body))
                    i = len(tokens) - len(remaining)

                elif tag_type in ("endif", "endfor"):
                    if end_tag is None:
                        raise TemplateSyntaxError(f"Unexpected {{% {tag_type} %}}")
                    expected_end = end_tag
                    if tag_type != expected_end:
                        raise TemplateSyntaxError(
                            f"Expected {{% {expected_end} %}} but got {{% {tag_type} %}}"
                        )
                    return nodes, tokens[i + 1:]
                else:
                    i += 1
            else:
                i += 1

        if end_tag is not None:
            raise TemplateSyntaxError(f"Missing {{% {end_tag} %}}")

        return nodes, []

    def _execute(self, nodes: List, context: Dict[str, Any]) -> str:
        """Execute a parsed tree against a context."""
        parts = []

        for node in nodes:
            if node[0] == "text":
                parts.append(node[1])

            elif node[0] == "var":
                parts.append(self._resolve_var(node[1], context))

            elif node[0] == "if":
                _, condition, body = node
                value = self._resolve_value(condition, context)
                if value:
                    parts.append(self._execute(body, context))

            elif node[0] == "for":
                _, var_name, iter_name, body = node
                iterable = context.get(iter_name, [])
                if not hasattr(iterable, "__iter__"):
                    raise TemplateSyntaxError(
                        f"'{iter_name}' is not iterable"
                    )
                for item in iterable:
                    child_ctx = {**context, var_name: item}
                    parts.append(self._execute(body, child_ctx))

        return "".join(parts)

    def _resolve_var(self, expr: str, context: Dict[str, Any]) -> str:
        """Resolve a variable expression with optional filters."""
        parts = expr.split("|")
        var_name = parts[0].strip()
        value = self._resolve_value(var_name, context)

        for filter_name in parts[1:]:
            filter_name = filter_name.strip()
            if filter_name in self.FILTERS:
                value = self.FILTERS[filter_name](value)
            else:
                raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")

        return str(value)

    def _resolve_value(self, name: str, context: Dict[str, Any]) -> Any:
        """Resolve a dotted variable name from context."""
        parts = name.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                value = getattr(value, part, "")
        return value


def render(template: str, context: Dict[str, Any]) -> str:
    """Convenience function to render a template."""
    engine = TemplateEngine()
    return engine.render(template, context)


if __name__ == "__main__":
    # Basic variable substitution
    print(render("Hello, {{ name }}!", {"name": "World"}))

    # Filters
    print(render("{{ name|upper }}, {{ name|lower }}, {{ name|title }}", {"name": "hello world"}))

    # Conditionals
    tmpl_if = "{% if show %}Visible{% endif %} Always"
    print(render(tmpl_if, {"show": True}))
    print(render(tmpl_if, {"show": False}))

    # Loops
    tmpl_for = "Items: {% for item in items %}[{{ item }}] {% endfor %}"
    print(render(tmpl_for, {"items": ["apple", "banana", "cherry"]}))

    # Nested blocks
    tmpl_nested = """{% for user in users %}{% if user.active %}{{ user.name|upper }}: active
{% endif %}{% endfor %}"""
    users = [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
        {"name": "Charlie", "active": True},
    ]
    print(render(tmpl_nested, {"users": users}))

    # Syntax error test
    try:
        render("{% if %}oops{% endif %}", {})
    except TemplateSyntaxError as e:
        print(f"TemplateSyntaxError: {e}")

    try:
        render("{% for x in items %}no end", {"items": [1]})
    except TemplateSyntaxError as e:
        print(f"TemplateSyntaxError: {e}")
