"""Template Engine — Python 3.10+ standard library only."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Union


# ─── Custom Exception ─────────────────────────────────────────


class TemplateSyntaxError(Exception):
    """Raised when a template has malformed syntax."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        if line is not None:
            super().__init__(f"TemplateSyntaxError at line {line}: {message}")
        else:
            super().__init__(f"TemplateSyntaxError: {message}")


# ─── AST Nodes ────────────────────────────────────────────────


@dataclass
class TextNode:
    content: str


@dataclass
class VarNode:
    name: str
    filters: list[str]


@dataclass
class IfNode:
    condition: str
    body: list[Node]
    else_body: list[Node]


@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: list[Node]


@dataclass
class Template:
    nodes: list[Node]


Node = Union[TextNode, VarNode, IfNode, ForNode]


# ─── Token Types ──────────────────────────────────────────────


@dataclass
class Token:
    type: str  # TEXT, VAR, IF, ELSE, ENDIF, FOR, ENDFOR
    value: str
    line: int


# ─── Regex Patterns ───────────────────────────────────────────

TAG_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)
VAR_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
IF_RE = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ELSE_RE = re.compile(r"\{%\s*else\s*%\}")
ENDIF_RE = re.compile(r"\{%\s*endif\s*%\}")
FOR_RE = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_RE = re.compile(r"\{%\s*endfor\s*%\}")


# ─── Tokenizer ────────────────────────────────────────────────


def tokenize(template: str) -> list[Token]:
    tokens: list[Token] = []
    last_end = 0
    line = 1

    for match in TAG_RE.finditer(template):
        start, end = match.span()

        # Text before this tag
        if start > last_end:
            text = template[last_end:start]
            tokens.append(Token(type="TEXT", value=text, line=line))
            line += text.count("\n")

        tag = match.group(0)

        m = VAR_RE.match(tag)
        if m:
            tokens.append(Token(type="VAR", value=m.group(1).strip(), line=line))
            line += tag.count("\n")
            last_end = end
            continue

        m = IF_RE.match(tag)
        if m:
            tokens.append(Token(type="IF", value=m.group(1).strip(), line=line))
            line += tag.count("\n")
            last_end = end
            continue

        m = ELSE_RE.match(tag)
        if m:
            tokens.append(Token(type="ELSE", value="", line=line))
            line += tag.count("\n")
            last_end = end
            continue

        m = ENDIF_RE.match(tag)
        if m:
            tokens.append(Token(type="ENDIF", value="", line=line))
            line += tag.count("\n")
            last_end = end
            continue

        m = FOR_RE.match(tag)
        if m:
            tokens.append(Token(type="FOR", value=f"{m.group(1)} in {m.group(2)}", line=line))
            line += tag.count("\n")
            last_end = end
            continue

        m = ENDFOR_RE.match(tag)
        if m:
            tokens.append(Token(type="ENDFOR", value="", line=line))
            line += tag.count("\n")
            last_end = end
            continue

        # Unknown tag
        raise TemplateSyntaxError(f"Unknown tag: {tag}", line=line)

    # Remaining text
    if last_end < len(template):
        text = template[last_end:]
        if text:
            tokens.append(Token(type="TEXT", value=text, line=line))

    return tokens


# ─── Parser ───────────────────────────────────────────────────


def parse_tokens(tokens: list[Token]) -> list[Node]:
    pos = 0
    nodes, pos = _parse_body(tokens, pos, stop_types=set())
    if pos < len(tokens):
        tok = tokens[pos]
        raise TemplateSyntaxError(f"Unexpected {tok.type} tag", line=tok.line)
    return nodes


def _parse_body(
    tokens: list[Token], pos: int, stop_types: set[str]
) -> tuple[list[Node], int]:
    nodes: list[Node] = []

    while pos < len(tokens):
        tok = tokens[pos]

        if tok.type in stop_types:
            return nodes, pos

        if tok.type == "TEXT":
            nodes.append(TextNode(content=tok.value))
            pos += 1

        elif tok.type == "VAR":
            parts = tok.value.split("|")
            name = parts[0].strip()
            filters = [f.strip() for f in parts[1:]]
            if not name:
                raise TemplateSyntaxError("Empty variable expression", line=tok.line)
            nodes.append(VarNode(name=name, filters=filters))
            pos += 1

        elif tok.type == "IF":
            condition = tok.value
            if_line = tok.line
            pos += 1
            body, pos = _parse_body(tokens, pos, stop_types={"ELSE", "ENDIF"})

            else_body: list[Node] = []
            if pos < len(tokens) and tokens[pos].type == "ELSE":
                pos += 1
                else_body, pos = _parse_body(tokens, pos, stop_types={"ENDIF"})

            if pos >= len(tokens) or tokens[pos].type != "ENDIF":
                raise TemplateSyntaxError("Unclosed {% if %} block", line=if_line)
            pos += 1  # skip ENDIF

            nodes.append(IfNode(condition=condition, body=body, else_body=else_body))

        elif tok.type == "FOR":
            for_line = tok.line
            parts = tok.value.split(" in ")
            var_name = parts[0].strip()
            iterable_name = parts[1].strip()
            pos += 1
            body, pos = _parse_body(tokens, pos, stop_types={"ENDFOR"})

            if pos >= len(tokens) or tokens[pos].type != "ENDFOR":
                raise TemplateSyntaxError("Unclosed {% for %} block", line=for_line)
            pos += 1  # skip ENDFOR

            nodes.append(ForNode(var_name=var_name, iterable_name=iterable_name, body=body))

        elif tok.type == "ENDIF":
            raise TemplateSyntaxError("Unexpected {% endif %}", line=tok.line)

        elif tok.type == "ENDFOR":
            raise TemplateSyntaxError("Unexpected {% endfor %}", line=tok.line)

        elif tok.type == "ELSE":
            raise TemplateSyntaxError("Unexpected {% else %} outside {% if %} block", line=tok.line)

        else:
            pos += 1

    return nodes, pos


# ─── Context Resolution ──────────────────────────────────────


def resolve_var(name: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted variable name from context."""
    parts = name.split(".")
    current: Any = context

    for part in parts:
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return ""
        else:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return ""

    return current


# ─── Condition Evaluation ─────────────────────────────────────


COMPARISON_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


def _try_parse_literal(s: str, context: dict[str, Any]) -> Any:
    """Try to parse a literal value or resolve from context."""
    s = s.strip()

    if not s:
        return ""

    # String literals
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]

    # Boolean literals
    if s == "True" or s == "true":
        return True
    if s == "False" or s == "false":
        return False
    if s == "None" or s == "none":
        return None

    # Numeric literals
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass

    # Variable resolution
    return resolve_var(s, context)


def evaluate_condition(expr: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition expression. Supports or, and, not, comparisons, and simple truthy."""
    expr = expr.strip()

    # Handle 'or'
    or_parts = _split_outside_strings(expr, " or ")
    if len(or_parts) > 1:
        return any(evaluate_condition(p, context) for p in or_parts)

    # Handle 'and'
    and_parts = _split_outside_strings(expr, " and ")
    if len(and_parts) > 1:
        return all(evaluate_condition(p, context) for p in and_parts)

    # Handle 'not'
    if expr.startswith("not "):
        return not evaluate_condition(expr[4:], context)

    # Handle comparison operators
    for op in ("==", "!=", ">=", "<=", ">", "<"):
        idx = expr.find(op)
        if idx != -1:
            left_str = expr[:idx].strip()
            right_str = expr[idx + len(op):].strip()
            left = _try_parse_literal(left_str, context)
            right = _try_parse_literal(right_str, context)
            try:
                return COMPARISON_OPS[op](left, right)
            except TypeError:
                return False

    # Simple truthy check
    val = _try_parse_literal(expr, context)
    return bool(val)


def _split_outside_strings(s: str, delimiter: str) -> list[str]:
    """Split string by delimiter, but not inside quotes."""
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    i = 0

    while i < len(s):
        if s[i] in ('"', "'") and in_quote is None:
            in_quote = s[i]
            current.append(s[i])
        elif s[i] == in_quote:
            in_quote = None
            current.append(s[i])
        elif in_quote is None and s[i:i + len(delimiter)] == delimiter:
            parts.append("".join(current))
            current = []
            i += len(delimiter)
            continue
        else:
            current.append(s[i])
        i += 1

    parts.append("".join(current))
    return parts


# ─── Renderer ─────────────────────────────────────────────────


def render_nodes(nodes: list[Node], context: dict[str, Any], filters: dict[str, Callable[[str], str]]) -> str:
    output_parts: list[str] = []

    for node in nodes:
        if isinstance(node, TextNode):
            output_parts.append(node.content)

        elif isinstance(node, VarNode):
            value = resolve_var(node.name, context)
            result = str(value) if value is not None else ""
            for f_name in node.filters:
                if f_name not in filters:
                    raise TemplateSyntaxError(f"Unknown filter: {f_name}")
                result = filters[f_name](result)
            output_parts.append(result)

        elif isinstance(node, IfNode):
            if evaluate_condition(node.condition, context):
                output_parts.append(render_nodes(node.body, context, filters))
            else:
                output_parts.append(render_nodes(node.else_body, context, filters))

        elif isinstance(node, ForNode):
            iterable = resolve_var(node.iterable_name, context)
            if iterable and hasattr(iterable, "__iter__"):
                for item in iterable:
                    child_context = {**context, node.var_name: item}
                    output_parts.append(render_nodes(node.body, child_context, filters))

    return "".join(output_parts)


# ─── Template Engine ──────────────────────────────────────────


class TemplateEngine:
    """Template engine supporting variables, conditionals, loops, and filter pipes."""

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
        nodes = parse_tokens(tokens)
        return Template(nodes=nodes)

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render a template string with the given context."""
        parsed = self.parse(template)
        return render_nodes(parsed.nodes, context, self._filters)


# ─── Main (demonstration) ────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    # Variable substitution
    result = engine.render("Hello, {{name}}!", {"name": "World"})
    print(result)

    # Filters
    result = engine.render("{{name|upper}}", {"name": "alice"})
    print(result)

    # Filter chaining
    result = engine.render("{{name|upper|capitalize}}", {"name": "hello world"})
    print(result)

    # Conditionals
    template = "{% if show %}Visible{% else %}Hidden{% endif %}"
    print(engine.render(template, {"show": True}))
    print(engine.render(template, {"show": False}))

    # Comparison
    template = "{% if count > 0 %}Positive{% else %}Zero or negative{% endif %}"
    print(engine.render(template, {"count": 5}))
    print(engine.render(template, {"count": 0}))

    # Loops
    template = "{% for item in items %}{{item}}, {% endfor %}"
    print(engine.render(template, {"items": ["a", "b", "c"]}))

    # Nested
    template = """{% for user in users %}
{{user.name}}: {% if user.active %}Active{% else %}Inactive{% endif %}
{% endfor %}"""
    context = {
        "users": [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
        ]
    }
    print(engine.render(template, context))

    # Dot notation
    result = engine.render("{{user.name|upper}}", {"user": {"name": "charlie"}})
    print(result)
