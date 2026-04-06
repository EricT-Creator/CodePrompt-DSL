from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Exceptions ───────────────────────────────────────────────────────────────

class TemplateSyntaxError(Exception):
    def __init__(self, message: str, position: int = -1) -> None:
        self.position: int = position
        prefix = f"[pos {position}] " if position >= 0 else ""
        super().__init__(f"{prefix}{message}")


# ─── AST Nodes ────────────────────────────────────────────────────────────────

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
    body: list[Any] = field(default_factory=list)


@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: list[Any] = field(default_factory=list)


@dataclass
class BlockNode:
    children: list[Any] = field(default_factory=list)


Node = TextNode | VarNode | IfNode | ForNode | BlockNode


# ─── Filter Registry ─────────────────────────────────────────────────────────

FILTERS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
    "strip": str.strip,
    "title": str.title,
}


# ─── Regex Patterns ──────────────────────────────────────────────────────────

_TOKENIZER_PATTERN = re.compile(
    r"(\{\{.*?\}\}|\{%\s*if\s+.*?%\}|\{%\s*endif\s*%\}|\{%\s*for\s+.*?%\}|\{%\s*endfor\s*%\})"
)
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF_PATTERN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_ENDIF_PATTERN = re.compile(r"\{%\s*endif\s*%\}")
_FOR_PATTERN = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_ENDFOR_PATTERN = re.compile(r"\{%\s*endfor\s*%\}")


# ─── Tokenizer ───────────────────────────────────────────────────────────────

@dataclass
class Token:
    kind: str  # TEXT, VAR, IF_OPEN, ENDIF, FOR_OPEN, ENDFOR
    value: str
    position: int


def tokenize(template: str) -> list[Token]:
    tokens: list[Token] = []
    last_end: int = 0

    for match in _TOKENIZER_PATTERN.finditer(template):
        start, end = match.start(), match.end()
        if start > last_end:
            tokens.append(Token(kind="TEXT", value=template[last_end:start], position=last_end))

        raw: str = match.group(0)
        pos: int = start

        if _VAR_PATTERN.match(raw):
            tokens.append(Token(kind="VAR", value=raw, position=pos))
        elif _IF_PATTERN.match(raw):
            tokens.append(Token(kind="IF_OPEN", value=raw, position=pos))
        elif _ENDIF_PATTERN.match(raw):
            tokens.append(Token(kind="ENDIF", value=raw, position=pos))
        elif _FOR_PATTERN.match(raw):
            tokens.append(Token(kind="FOR_OPEN", value=raw, position=pos))
        elif _ENDFOR_PATTERN.match(raw):
            tokens.append(Token(kind="ENDFOR", value=raw, position=pos))
        else:
            raise TemplateSyntaxError(f"Unrecognized tag: {raw}", position=pos)

        last_end = end

    if last_end < len(template):
        tokens.append(Token(kind="TEXT", value=template[last_end:], position=last_end))

    return tokens


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse(tokens: list[Token]) -> BlockNode:
    root = BlockNode()
    stack: list[BlockNode | IfNode | ForNode] = [root]

    for token in tokens:
        current = stack[-1]
        children: list[Any]

        if isinstance(current, BlockNode):
            children = current.children
        elif isinstance(current, (IfNode, ForNode)):
            children = current.body
        else:
            raise TemplateSyntaxError("Invalid parser state", position=token.position)

        if token.kind == "TEXT":
            if token.value:
                children.append(TextNode(content=token.value))

        elif token.kind == "VAR":
            m = _VAR_PATTERN.match(token.value)
            if not m:
                raise TemplateSyntaxError(f"Invalid variable syntax: {token.value}", position=token.position)
            parts = m.group(1).split("|")
            var_name = parts[0]
            filters = parts[1:]
            for f in filters:
                if f not in FILTERS:
                    raise TemplateSyntaxError(f"Unknown filter: '{f}'", position=token.position)
            children.append(VarNode(name=var_name, filters=filters))

        elif token.kind == "IF_OPEN":
            m = _IF_PATTERN.match(token.value)
            if not m:
                raise TemplateSyntaxError(f"Invalid if syntax: {token.value}", position=token.position)
            condition = m.group(1).strip()
            node = IfNode(condition=condition)
            children.append(node)
            stack.append(node)

        elif token.kind == "ENDIF":
            if not isinstance(stack[-1], IfNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endif %}: no matching {% if %}",
                    position=token.position,
                )
            stack.pop()

        elif token.kind == "FOR_OPEN":
            m = _FOR_PATTERN.match(token.value)
            if not m:
                raise TemplateSyntaxError(f"Invalid for syntax: {token.value}", position=token.position)
            var_name = m.group(1)
            iterable_name = m.group(2)
            node = ForNode(var_name=var_name, iterable_name=iterable_name)
            children.append(node)
            stack.append(node)

        elif token.kind == "ENDFOR":
            if not isinstance(stack[-1], ForNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endfor %}: no matching {% for %}",
                    position=token.position,
                )
            stack.pop()

    if len(stack) != 1:
        top = stack[-1]
        tag_type = "if" if isinstance(top, IfNode) else "for" if isinstance(top, ForNode) else "unknown"
        raise TemplateSyntaxError(f"Unclosed {{% {tag_type} %}} block")

    return root


# ─── Renderer ─────────────────────────────────────────────────────────────────

def render_node(node: Any, context: dict[str, Any]) -> str:
    if isinstance(node, TextNode):
        return node.content

    if isinstance(node, VarNode):
        value = context.get(node.name, "")
        result = str(value)
        for filter_name in node.filters:
            fn = FILTERS[filter_name]
            result = fn(result)
        return result

    if isinstance(node, IfNode):
        condition_value = context.get(node.condition)
        if condition_value:
            return "".join(render_node(child, context) for child in node.body)
        return ""

    if isinstance(node, ForNode):
        iterable = context.get(node.iterable_name)
        if iterable is None:
            return ""
        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(
                f"'{node.iterable_name}' is not iterable (got {type(iterable).__name__})"
            )
        parts: list[str] = []
        for item in iterable:
            child_ctx = {**context, node.var_name: item}
            for child in node.body:
                parts.append(render_node(child, child_ctx))
        return "".join(parts)

    if isinstance(node, BlockNode):
        return "".join(render_node(child, context) for child in node.children)

    return ""


# ─── Template Engine ──────────────────────────────────────────────────────────

class TemplateEngine:
    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = dict(FILTERS)

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        self._filters[name] = fn
        FILTERS[name] = fn

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        ctx: dict[str, Any] = context if context is not None else {}
        tokens = tokenize(template)
        tree = parse(tokens)
        return render_node(tree, ctx)


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    template = """Hello, {{ name|upper }}!

{% if show_items %}Items:
{% for item in items %}- {{ item|capitalize }}
{% endfor %}{% endif %}

{% if footer %}Footer: {{ footer }}{% endif %}"""

    context: dict[str, Any] = {
        "name": "world",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
        "footer": "Generated by TemplateEngine",
    }

    result = engine.render(template, context)
    print(result)

    print("\n--- Nested test ---")
    nested_template = """{% for group in groups %}Group: {{ group }}
{% for item in items %}  - {{ item|upper }}
{% endfor %}{% endfor %}"""

    nested_ctx: dict[str, Any] = {
        "groups": ["A", "B"],
        "items": ["x", "y"],
    }
    print(engine.render(nested_template, nested_ctx))
