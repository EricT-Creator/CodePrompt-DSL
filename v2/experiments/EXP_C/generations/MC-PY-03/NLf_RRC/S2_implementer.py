"""Template Engine with variable substitution, conditionals, loops, and filters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Union


# ── Exceptions ───────────────────────────────────────────────────────────────


class TemplateSyntaxError(Exception):
    """Raised for malformed templates."""

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


@dataclass
class Template:
    nodes: list[Node] = field(default_factory=list)


Node = Union[TextNode, VarNode, IfNode, ForNode]


# ── Token Types ──────────────────────────────────────────────────────────────

TOKEN_TEXT = "TEXT"
TOKEN_VAR = "VAR"
TOKEN_IF = "IF"
TOKEN_ELSE = "ELSE"
TOKEN_ENDIF = "ENDIF"
TOKEN_FOR = "FOR"
TOKEN_ENDFOR = "ENDFOR"


@dataclass
class Token:
    type: str
    value: str
    line: int


# ── Regex Patterns ───────────────────────────────────────────────────────────

TAG_PATTERN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)

VAR_PATTERN = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*(?:\|[a-zA-Z_]+)*)\s*\}\}"
)

IF_PATTERN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ELSE_PATTERN = re.compile(r"\{%\s*else\s*%\}")
ENDIF_PATTERN = re.compile(r"\{%\s*endif\s*%\}")
FOR_PATTERN = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_PATTERN = re.compile(r"\{%\s*endfor\s*%\}")


# ── Tokenizer ────────────────────────────────────────────────────────────────


def tokenize(template: str) -> list[Token]:
    """Split template into tokens."""
    tokens: list[Token] = []
    line_num = 1

    parts = TAG_PATTERN.split(template)

    for part in parts:
        if not part:
            continue

        current_line = line_num
        line_num += part.count("\n")

        # Check tag type
        m_var = VAR_PATTERN.fullmatch(part)
        if m_var:
            tokens.append(Token(TOKEN_VAR, m_var.group(1).strip(), current_line))
            continue

        m_if = IF_PATTERN.fullmatch(part)
        if m_if:
            tokens.append(Token(TOKEN_IF, m_if.group(1).strip(), current_line))
            continue

        m_else = ELSE_PATTERN.fullmatch(part)
        if m_else:
            tokens.append(Token(TOKEN_ELSE, "", current_line))
            continue

        m_endif = ENDIF_PATTERN.fullmatch(part)
        if m_endif:
            tokens.append(Token(TOKEN_ENDIF, "", current_line))
            continue

        m_for = FOR_PATTERN.fullmatch(part)
        if m_for:
            tokens.append(
                Token(TOKEN_FOR, f"{m_for.group(1)}:{m_for.group(2)}", current_line)
            )
            continue

        m_endfor = ENDFOR_PATTERN.fullmatch(part)
        if m_endfor:
            tokens.append(Token(TOKEN_ENDFOR, "", current_line))
            continue

        # Check for malformed tags
        stripped = part.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            inner = stripped[2:-2].strip()
            if not inner:
                raise TemplateSyntaxError("Empty variable expression", current_line)
            raise TemplateSyntaxError(
                f"Invalid variable syntax: {stripped}", current_line
            )

        if stripped.startswith("{%") and stripped.endswith("%}"):
            raise TemplateSyntaxError(
                f"Unrecognized tag: {stripped}", current_line
            )

        # Plain text
        tokens.append(Token(TOKEN_TEXT, part, current_line))

    return tokens


# ── Parser ───────────────────────────────────────────────────────────────────


def parse_tokens(tokens: list[Token]) -> list[Node]:
    """Parse a flat token list into an AST node list."""
    pos = 0
    nodes, pos = _parse_block(tokens, pos, set())
    return nodes


def _parse_block(
    tokens: list[Token],
    pos: int,
    stop_types: set[str],
) -> tuple[list[Node], int]:
    """Parse tokens until a stop token type is encountered."""
    nodes: list[Node] = []

    while pos < len(tokens):
        token = tokens[pos]

        if token.type in stop_types:
            return nodes, pos

        if token.type == TOKEN_TEXT:
            nodes.append(TextNode(content=token.value))
            pos += 1

        elif token.type == TOKEN_VAR:
            parts = token.value.split("|")
            name = parts[0].strip()
            filters = [f.strip() for f in parts[1:]]
            nodes.append(VarNode(name=name, filters=filters))
            pos += 1

        elif token.type == TOKEN_IF:
            condition = token.value
            pos += 1

            body, pos = _parse_block(
                tokens, pos, {TOKEN_ELSE, TOKEN_ENDIF}
            )

            else_body: list[Node] = []
            if pos < len(tokens) and tokens[pos].type == TOKEN_ELSE:
                pos += 1
                else_body, pos = _parse_block(tokens, pos, {TOKEN_ENDIF})

            if pos >= len(tokens) or tokens[pos].type != TOKEN_ENDIF:
                raise TemplateSyntaxError(
                    "Unclosed {% if %} block",
                    token.line,
                )

            pos += 1  # skip ENDIF
            nodes.append(
                IfNode(condition=condition, body=body, else_body=else_body)
            )

        elif token.type == TOKEN_FOR:
            parts = token.value.split(":")
            var_name = parts[0]
            iterable_name = parts[1] if len(parts) > 1 else ""
            pos += 1

            body, pos = _parse_block(tokens, pos, {TOKEN_ENDFOR})

            if pos >= len(tokens) or tokens[pos].type != TOKEN_ENDFOR:
                raise TemplateSyntaxError(
                    "Unclosed {% for %} block",
                    token.line,
                )

            pos += 1  # skip ENDFOR
            nodes.append(
                ForNode(var_name=var_name, iterable_name=iterable_name, body=body)
            )

        elif token.type == TOKEN_ENDIF:
            raise TemplateSyntaxError(
                "Unexpected {% endif %} without matching {% if %}",
                token.line,
            )

        elif token.type == TOKEN_ENDFOR:
            raise TemplateSyntaxError(
                "Unexpected {% endfor %} without matching {% for %}",
                token.line,
            )

        elif token.type == TOKEN_ELSE:
            raise TemplateSyntaxError(
                "Unexpected {% else %} outside an {% if %} block",
                token.line,
            )

        else:
            pos += 1

    return nodes, pos


# ── Condition Evaluator ──────────────────────────────────────────────────────

COMPARISON_RE = re.compile(
    r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$"
)


def resolve_var(name: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted variable name from context."""
    parts = name.strip().split(".")
    current: Any = context

    for part in parts:
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return ""
        else:
            current = getattr(current, part, "")

    return current


def _coerce_value(raw: str, context: dict[str, Any]) -> Any:
    """Try to interpret a raw string as a literal or variable reference."""
    raw = raw.strip()

    # String literal
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]

    # Boolean literals
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if raw.lower() == "none":
        return None

    # Numeric literal
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass

    # Variable reference
    return resolve_var(raw, context)


def evaluate_condition(expr: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition expression with support for and/or/not and comparisons."""
    expr = expr.strip()

    # Handle 'or'
    or_parts = _split_keyword(expr, " or ")
    if len(or_parts) > 1:
        return any(evaluate_condition(p, context) for p in or_parts)

    # Handle 'and'
    and_parts = _split_keyword(expr, " and ")
    if len(and_parts) > 1:
        return all(evaluate_condition(p, context) for p in and_parts)

    # Handle 'not'
    if expr.startswith("not "):
        return not evaluate_condition(expr[4:], context)

    # Handle comparison
    m = COMPARISON_RE.match(expr)
    if m:
        left = _coerce_value(m.group(1), context)
        op = m.group(2)
        right = _coerce_value(m.group(3), context)

        try:
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            if op == ">=":
                return left >= right
            if op == "<=":
                return left <= right
        except TypeError:
            return False

    # Simple truthy check
    val = _coerce_value(expr, context)
    return bool(val)


def _split_keyword(expr: str, keyword: str) -> list[str]:
    """Split an expression by a keyword, respecting parentheses depth (simple)."""
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
        elif depth == 0 and expr[i:].startswith(keyword):
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


def render_nodes(
    nodes: list[Node],
    context: dict[str, Any],
    filters: dict[str, Callable[[str], str]],
) -> str:
    """Render a list of AST nodes to a string."""
    output: list[str] = []

    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.content)

        elif isinstance(node, VarNode):
            value = resolve_var(node.name, context)
            result = str(value) if value is not None else ""

            for filter_name in node.filters:
                fn = filters.get(filter_name)
                if fn is None:
                    raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
                result = fn(result)

            output.append(result)

        elif isinstance(node, IfNode):
            if evaluate_condition(node.condition, context):
                output.append(render_nodes(node.body, context, filters))
            else:
                output.append(render_nodes(node.else_body, context, filters))

        elif isinstance(node, ForNode):
            iterable = resolve_var(node.iterable_name, context)
            if iterable and hasattr(iterable, "__iter__"):
                for item in iterable:
                    child_context = {**context, node.var_name: item}
                    output.append(render_nodes(node.body, child_context, filters))

    return "".join(output)


# ── TemplateEngine ───────────────────────────────────────────────────────────


class TemplateEngine:
    """Template engine with variable substitution, conditionals, loops, and filters."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render a template string."""
        parsed = self.parse(template)
        return render_nodes(parsed.nodes, context, self._filters)

    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    def parse(self, template: str) -> Template:
        """Parse a template string into an AST."""
        tokens = tokenize(template)
        nodes = parse_tokens(tokens)
        return Template(nodes=nodes)


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    template = """Hello, {{ name|upper }}!

{% if show_items %}Items:
{% for item in items %}- {{ item.name }}: ${{ item.price }}
{% endfor %}{% else %}No items to display.{% endif %}

{% if count > 0 %}Count is positive: {{ count }}{% endif %}
"""

    ctx: dict[str, Any] = {
        "name": "world",
        "show_items": True,
        "items": [
            {"name": "Widget", "price": "9.99"},
            {"name": "Gadget", "price": "19.99"},
            {"name": "Doohickey", "price": "4.50"},
        ],
        "count": 3,
    }

    result = engine.render(template, ctx)
    print(result)
