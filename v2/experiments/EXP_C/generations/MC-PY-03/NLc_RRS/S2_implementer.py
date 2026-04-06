from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Exceptions ──

class TemplateSyntaxError(Exception):
    def __init__(self, message: str, position: int = -1) -> None:
        self.position: int = position
        msg = f"{message} (at position {position})" if position >= 0 else message
        super().__init__(msg)


# ── AST Nodes ──

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


@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: list[Node] = field(default_factory=list)


@dataclass
class BlockNode:
    children: list[Node] = field(default_factory=list)


Node = TextNode | VarNode | IfNode | ForNode | BlockNode


# ── Token Types ──

@dataclass
class Token:
    token_type: str  # TEXT, VAR, IF_OPEN, ENDIF, FOR_OPEN, ENDFOR
    value: str
    position: int


# ── Filter Registry ──

FILTERS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
}


# ── Regex Patterns ──

COMBINED_PATTERN: re.Pattern[str] = re.compile(
    r"(\{\{.*?\}\}|\{%\s*if\s+.*?%\}|\{%\s*endif\s*%\}|\{%\s*for\s+.*?%\}|\{%\s*endfor\s*%\})"
)

VAR_PATTERN: re.Pattern[str] = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
IF_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ENDIF_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*endif\s*%\}")
FOR_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*endfor\s*%\}")


# ── Tokenizer ──

def tokenize(template: str) -> list[Token]:
    tokens: list[Token] = []
    last_end: int = 0

    for match in COMBINED_PATTERN.finditer(template):
        start: int = match.start()
        end: int = match.end()

        if start > last_end:
            tokens.append(Token(token_type="TEXT", value=template[last_end:start], position=last_end))

        raw: str = match.group(0)

        var_match = VAR_PATTERN.fullmatch(raw)
        if var_match:
            tokens.append(Token(token_type="VAR", value=var_match.group(1), position=start))
            last_end = end
            continue

        if_match = IF_PATTERN.fullmatch(raw)
        if if_match:
            tokens.append(Token(token_type="IF_OPEN", value=if_match.group(1).strip(), position=start))
            last_end = end
            continue

        if ENDIF_PATTERN.fullmatch(raw):
            tokens.append(Token(token_type="ENDIF", value="", position=start))
            last_end = end
            continue

        for_match = FOR_PATTERN.fullmatch(raw)
        if for_match:
            tokens.append(Token(
                token_type="FOR_OPEN",
                value=f"{for_match.group(1)}:{for_match.group(2)}",
                position=start,
            ))
            last_end = end
            continue

        if ENDFOR_PATTERN.fullmatch(raw):
            tokens.append(Token(token_type="ENDFOR", value="", position=start))
            last_end = end
            continue

        raise TemplateSyntaxError(f"Unrecognized tag: {raw}", position=start)

    if last_end < len(template):
        tokens.append(Token(token_type="TEXT", value=template[last_end:], position=last_end))

    return tokens


# ── Parser ──

def parse(tokens: list[Token]) -> BlockNode:
    root = BlockNode()
    stack: list[BlockNode | IfNode | ForNode] = [root]

    for token in tokens:
        current = stack[-1]

        if token.token_type == "TEXT":
            children = _get_children(current)
            children.append(TextNode(content=token.value))

        elif token.token_type == "VAR":
            parts: list[str] = token.value.split("|")
            var_name: str = parts[0]
            filters: list[str] = parts[1:]
            for f in filters:
                if f not in FILTERS:
                    raise TemplateSyntaxError(f"Unknown filter: '{f}'", position=token.position)
            children = _get_children(current)
            children.append(VarNode(name=var_name, filters=filters))

        elif token.token_type == "IF_OPEN":
            if_node = IfNode(condition=token.value)
            children = _get_children(current)
            children.append(if_node)
            stack.append(if_node)

        elif token.token_type == "ENDIF":
            if not isinstance(current, IfNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endif %}: no matching {% if %}",
                    position=token.position,
                )
            stack.pop()

        elif token.token_type == "FOR_OPEN":
            parts_for: list[str] = token.value.split(":")
            for_node = ForNode(var_name=parts_for[0], iterable_name=parts_for[1])
            children = _get_children(current)
            children.append(for_node)
            stack.append(for_node)

        elif token.token_type == "ENDFOR":
            if not isinstance(current, ForNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endfor %}: no matching {% for %}",
                    position=token.position,
                )
            stack.pop()

    if len(stack) != 1:
        top = stack[-1]
        if isinstance(top, IfNode):
            raise TemplateSyntaxError("Unclosed {% if %} block")
        if isinstance(top, ForNode):
            raise TemplateSyntaxError("Unclosed {% for %} block")
        raise TemplateSyntaxError("Unclosed block")

    return root


def _get_children(node: BlockNode | IfNode | ForNode) -> list[Node]:
    if isinstance(node, BlockNode):
        return node.children
    if isinstance(node, IfNode):
        return node.body
    if isinstance(node, ForNode):
        return node.body
    raise TemplateSyntaxError("Invalid node type on stack")


# ── Renderer ──

def render(node: Node, context: dict[str, Any]) -> str:
    if isinstance(node, TextNode):
        return node.content

    if isinstance(node, VarNode):
        value: Any = context.get(node.name, "")
        result: str = str(value)
        for filter_name in node.filters:
            fn = FILTERS.get(filter_name)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")
            result = fn(result)
        return result

    if isinstance(node, IfNode):
        condition_value: Any = context.get(node.condition)
        if condition_value:
            return "".join(render(child, context) for child in node.body)
        return ""

    if isinstance(node, ForNode):
        iterable: Any = context.get(node.iterable_name)
        if iterable is None:
            return ""
        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(
                f"'{node.iterable_name}' is not iterable"
            )
        parts: list[str] = []
        for item in iterable:
            child_context: dict[str, Any] = {**context, node.var_name: item}
            for child in node.body:
                parts.append(render(child, child_context))
        return "".join(parts)

    if isinstance(node, BlockNode):
        return "".join(render(child, context) for child in node.children)

    return ""


# ── Template Engine (main class) ──

class TemplateEngine:
    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = dict(FILTERS)

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        self._filters[name] = fn
        FILTERS[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        tokens: list[Token] = tokenize(template)
        ast: BlockNode = parse(tokens)
        return render(ast, context)


# ── Example Usage ──

if __name__ == "__main__":
    engine = TemplateEngine()

    template_str = """Hello, {{name|upper}}!

{% if show_items %}Items:
{% for item in items %}- {{item|capitalize}}
{% endfor %}{% endif %}

Total: {{count}} items.
"""

    ctx: dict[str, Any] = {
        "name": "world",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
        "count": 3,
    }

    output: str = engine.render(template_str, ctx)
    print(output)

    try:
        engine.render("{% if x %}unclosed", {})
    except TemplateSyntaxError as e:
        print(f"Caught error: {e}")

    try:
        engine.render("{{name|nonexistent}}", {"name": "test"})
    except TemplateSyntaxError as e:
        print(f"Caught error: {e}")
