"""Template Engine — regex-parsed templates with variables, conditionals, loops, and filters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Union


# ── Custom Exception ─────────────────────────────────────────────────────────


class TemplateSyntaxError(Exception):
    """Raised for malformed template syntax."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line: int | None = line
        if line is not None:
            super().__init__(f"TemplateSyntaxError at line {line}: {message}")
        else:
            super().__init__(f"TemplateSyntaxError: {message}")


# ── AST Nodes ────────────────────────────────────────────────────────────────


@dataclass
class TextNode:
    content: str


@dataclass
class VarNode:
    name: str
    filters: list[str] = field(default_factory=list)


@dataclass
class IfNode:
    condition: str
    body: list[Node] = field(default_factory=list)
    else_body: list[Node] = field(default_factory=list)


@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: list[Node] = field(default_factory=list)


Node = Union[TextNode, VarNode, IfNode, ForNode]


@dataclass
class Template:
    nodes: list[Node]


# ── Token Types ──────────────────────────────────────────────────────────────

TOKEN_TEXT = "TEXT"
TOKEN_VAR = "VAR"
TOKEN_IF = "IF"
TOKEN_ELSE = "ELSE"
TOKEN_ENDIF = "ENDIF"
TOKEN_FOR = "FOR"
TOKEN_ENDFOR = "ENDFOR"

# ── Regex Patterns ───────────────────────────────────────────────────────────

RE_TAG = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})', re.DOTALL)
RE_VAR = re.compile(r'\{\{\s*(.+?)\s*\}\}')
RE_IF = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
RE_ELSE = re.compile(r'\{%\s*else\s*%\}')
RE_ENDIF = re.compile(r'\{%\s*endif\s*%\}')
RE_FOR = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
RE_ENDFOR = re.compile(r'\{%\s*endfor\s*%\}')


# ── Tokenizer ────────────────────────────────────────────────────────────────


@dataclass
class Token:
    type: str
    value: str
    meta: dict[str, str] = field(default_factory=dict)


def tokenize(template: str) -> list[Token]:
    """Split template into tokens."""
    tokens: list[Token] = []
    parts = RE_TAG.split(template)

    for part in parts:
        if not part:
            continue

        m_var = RE_VAR.match(part)
        m_if = RE_IF.match(part)
        m_else = RE_ELSE.match(part)
        m_endif = RE_ENDIF.match(part)
        m_for = RE_FOR.match(part)
        m_endfor = RE_ENDFOR.match(part)

        if m_if:
            tokens.append(Token(TOKEN_IF, part, {"condition": m_if.group(1).strip()}))
        elif m_else:
            tokens.append(Token(TOKEN_ELSE, part))
        elif m_endif:
            tokens.append(Token(TOKEN_ENDIF, part))
        elif m_for:
            tokens.append(Token(TOKEN_FOR, part, {
                "var_name": m_for.group(1),
                "iterable_name": m_for.group(2),
            }))
        elif m_endfor:
            tokens.append(Token(TOKEN_ENDFOR, part))
        elif m_var:
            raw = m_var.group(1).strip()
            if not raw:
                raise TemplateSyntaxError("Empty variable expression")
            tokens.append(Token(TOKEN_VAR, part, {"expression": raw}))
        else:
            tokens.append(Token(TOKEN_TEXT, part))

    return tokens


# ── Parser ───────────────────────────────────────────────────────────────────


def parse_tokens(tokens: list[Token], pos: int = 0) -> tuple[list[Node], int]:
    """Recursive descent parser for template tokens."""
    nodes: list[Node] = []

    while pos < len(tokens):
        token = tokens[pos]

        if token.type == TOKEN_TEXT:
            nodes.append(TextNode(content=token.value))
            pos += 1

        elif token.type == TOKEN_VAR:
            expr = token.meta["expression"]
            parts = expr.split("|")
            name = parts[0].strip()
            filters = [f.strip() for f in parts[1:] if f.strip()]
            nodes.append(VarNode(name=name, filters=filters))
            pos += 1

        elif token.type == TOKEN_IF:
            condition = token.meta["condition"]
            pos += 1
            body, pos = parse_tokens(tokens, pos)

            else_body: list[Node] = []
            if pos < len(tokens) and tokens[pos].type == TOKEN_ELSE:
                pos += 1
                else_body, pos = parse_tokens(tokens, pos)

            if pos >= len(tokens) or tokens[pos].type != TOKEN_ENDIF:
                raise TemplateSyntaxError("Unclosed {% if %} block — missing {% endif %}")
            pos += 1

            nodes.append(IfNode(condition=condition, body=body, else_body=else_body))

        elif token.type == TOKEN_FOR:
            var_name = token.meta["var_name"]
            iterable_name = token.meta["iterable_name"]
            pos += 1
            body, pos = parse_tokens(tokens, pos)

            if pos >= len(tokens) or tokens[pos].type != TOKEN_ENDFOR:
                raise TemplateSyntaxError("Unclosed {% for %} block — missing {% endfor %}")
            pos += 1

            nodes.append(ForNode(var_name=var_name, iterable_name=iterable_name, body=body))

        elif token.type in (TOKEN_ENDIF, TOKEN_ENDFOR, TOKEN_ELSE):
            # Return to parent parser
            break

        else:
            pos += 1

    return nodes, pos


# ── Condition Evaluator ──────────────────────────────────────────────────────


def resolve_var(name: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted variable name from context."""
    parts = name.strip().split(".")
    obj: Any = context
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part, "")
        else:
            obj = getattr(obj, part, "")
        if obj == "":
            break
    return obj


def _try_number(s: str) -> int | float | str:
    """Try to convert a string to a number."""
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _resolve_value(token: str, context: dict[str, Any]) -> Any:
    """Resolve a token: could be a string literal, number, or variable."""
    token = token.strip()
    # String literals
    if (token.startswith('"') and token.endswith('"')) or \
       (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    # Boolean literals
    if token == "True" or token == "true":
        return True
    if token == "False" or token == "false":
        return False
    if token == "None" or token == "none":
        return None
    # Number
    num = _try_number(token)
    if isinstance(num, (int, float)):
        return num
    # Variable
    return resolve_var(token, context)


COMPARISON_OPS = ["==", "!=", ">=", "<=", ">", "<"]


def evaluate_condition(expr: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition string with support for and/or/not and comparisons."""
    expr = expr.strip()

    # Handle 'or'
    or_parts = _split_on_keyword(expr, " or ")
    if len(or_parts) > 1:
        return any(evaluate_condition(p, context) for p in or_parts)

    # Handle 'and'
    and_parts = _split_on_keyword(expr, " and ")
    if len(and_parts) > 1:
        return all(evaluate_condition(p, context) for p in and_parts)

    # Handle 'not'
    if expr.startswith("not "):
        return not evaluate_condition(expr[4:], context)

    # Handle comparison operators
    for op in COMPARISON_OPS:
        if op in expr:
            parts = expr.split(op, 1)
            if len(parts) == 2:
                left = _resolve_value(parts[0], context)
                right = _resolve_value(parts[1], context)
                if op == "==":
                    return left == right
                elif op == "!=":
                    return left != right
                elif op == ">":
                    return left > right
                elif op == "<":
                    return left < right
                elif op == ">=":
                    return left >= right
                elif op == "<=":
                    return left <= right

    # Simple truthy check
    value = _resolve_value(expr, context)
    return bool(value)


def _split_on_keyword(expr: str, keyword: str) -> list[str]:
    """Split expression on keyword, respecting parentheses (simple)."""
    parts: list[str] = []
    depth = 0
    current = ""
    i = 0
    while i < len(expr):
        if expr[i] == "(":
            depth += 1
            current += expr[i]
        elif expr[i] == ")":
            depth -= 1
            current += expr[i]
        elif depth == 0 and expr[i:i + len(keyword)] == keyword:
            parts.append(current)
            current = ""
            i += len(keyword)
            continue
        else:
            current += expr[i]
        i += 1
    if current:
        parts.append(current)
    return parts


# ── Renderer ─────────────────────────────────────────────────────────────────


class TemplateEngine:
    """Template engine with variable substitution, conditionals, loops, and filters."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    def parse(self, template: str) -> Template:
        """Parse a template string into an AST."""
        tokens = tokenize(template)
        nodes, pos = parse_tokens(tokens)

        # Check for unexpected remaining tokens
        if pos < len(tokens):
            remaining = tokens[pos]
            if remaining.type == TOKEN_ENDIF:
                raise TemplateSyntaxError("Unexpected {% endif %} without matching {% if %}")
            elif remaining.type == TOKEN_ENDFOR:
                raise TemplateSyntaxError("Unexpected {% endfor %} without matching {% for %}")
            elif remaining.type == TOKEN_ELSE:
                raise TemplateSyntaxError("Unexpected {% else %} outside an {% if %} block")

        return Template(nodes=nodes)

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render a template string."""
        ast = self.parse(template)
        return self._render_nodes(ast.nodes, context)

    def _render_nodes(self, nodes: list[Node], context: dict[str, Any]) -> str:
        """Render a list of AST nodes."""
        output: list[str] = []
        for node in nodes:
            output.append(self._render_node(node, context))
        return "".join(output)

    def _render_node(self, node: Node, context: dict[str, Any]) -> str:
        """Render a single AST node."""
        if isinstance(node, TextNode):
            return node.content

        elif isinstance(node, VarNode):
            value = resolve_var(node.name, context)
            result = str(value) if value is not None else ""
            for filter_name in node.filters:
                if filter_name not in self._filters:
                    raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
                result = self._filters[filter_name](result)
            return result

        elif isinstance(node, IfNode):
            if evaluate_condition(node.condition, context):
                return self._render_nodes(node.body, context)
            else:
                return self._render_nodes(node.else_body, context)

        elif isinstance(node, ForNode):
            iterable = resolve_var(node.iterable_name, context)
            if not hasattr(iterable, "__iter__"):
                return ""
            parts: list[str] = []
            for item in iterable:
                child_context = {**context, node.var_name: item}
                parts.append(self._render_nodes(node.body, child_context))
            return "".join(parts)

        return ""


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    # Simple variable
    print(engine.render("Hello, {{name}}!", {"name": "Alice"}))

    # Filters
    print(engine.render("{{name|upper}}", {"name": "alice"}))
    print(engine.render("{{name|upper|capitalize}}", {"name": "hello world"}))

    # Conditional
    template = "{% if show %}Visible{% else %}Hidden{% endif %}"
    print(engine.render(template, {"show": True}))
    print(engine.render(template, {"show": False}))

    # Comparison
    template = "{% if count > 0 %}Has items{% else %}Empty{% endif %}"
    print(engine.render(template, {"count": 5}))

    # Loop
    template = "{% for item in items %}{{item}}, {% endfor %}"
    print(engine.render(template, {"items": ["a", "b", "c"]}))

    # Nested
    template = """{% for user in users %}{% if user.active %}{{user.name|upper}} {% endif %}{% endfor %}"""
    context = {
        "users": [
            {"name": "alice", "active": True},
            {"name": "bob", "active": False},
            {"name": "carol", "active": True},
        ]
    }
    print(engine.render(template, context))

    # Dot notation
    print(engine.render("{{user.name}}", {"user": {"name": "Dave"}}))

    # Error handling
    try:
        engine.render("{% if x %}no end", {})
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")
