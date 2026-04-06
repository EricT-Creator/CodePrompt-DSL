from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ---- Exceptions ----

class TemplateSyntaxError(Exception):
    def __init__(self, message: str, position: int | None = None) -> None:
        self.position: int | None = position
        if position is not None:
            super().__init__(f"{message} (at position {position})")
        else:
            super().__init__(message)


# ---- AST Node Types ----

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


# ---- Filter Registry ----

FILTERS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
    "strip": str.strip,
    "title": str.title,
}


# ---- Regex Patterns ----

TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"(\{\{.*?\}\}|\{%\s*if\s+.*?%\}|\{%\s*endif\s*%\}|\{%\s*for\s+.*?%\}|\{%\s*endfor\s*%\})",
    re.DOTALL,
)

VAR_PATTERN: re.Pattern[str] = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
IF_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ENDIF_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*endif\s*%\}")
FOR_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_PATTERN: re.Pattern[str] = re.compile(r"\{%\s*endfor\s*%\}")


# ---- Tokenizer ----

@dataclass
class Token:
    type: str  # "TEXT", "VAR", "IF_OPEN", "ENDIF", "FOR_OPEN", "ENDFOR"
    value: str
    position: int


def tokenize(template: str) -> list[Token]:
    tokens: list[Token] = []
    last_end: int = 0

    for match in TOKEN_PATTERN.finditer(template):
        start = match.start()
        end = match.end()
        raw = match.group(0)

        # Text before this token
        if start > last_end:
            tokens.append(Token(type="TEXT", value=template[last_end:start], position=last_end))

        # Classify token
        if VAR_PATTERN.match(raw):
            tokens.append(Token(type="VAR", value=raw, position=start))
        elif IF_PATTERN.match(raw):
            tokens.append(Token(type="IF_OPEN", value=raw, position=start))
        elif ENDIF_PATTERN.match(raw):
            tokens.append(Token(type="ENDIF", value=raw, position=start))
        elif FOR_PATTERN.match(raw):
            tokens.append(Token(type="FOR_OPEN", value=raw, position=start))
        elif ENDFOR_PATTERN.match(raw):
            tokens.append(Token(type="ENDFOR", value=raw, position=start))
        else:
            raise TemplateSyntaxError(f"Unrecognized template tag: {raw}", position=start)

        last_end = end

    # Trailing text
    if last_end < len(template):
        tokens.append(Token(type="TEXT", value=template[last_end:], position=last_end))

    return tokens


# ---- Parser ----

def parse(tokens: list[Token]) -> BlockNode:
    root = BlockNode()
    stack: list[BlockNode | IfNode | ForNode] = [root]

    for token in tokens:
        current = stack[-1]

        if token.type == "TEXT":
            children = _get_children(current)
            children.append(TextNode(content=token.value))

        elif token.type == "VAR":
            match = VAR_PATTERN.match(token.value)
            if not match:
                raise TemplateSyntaxError(f"Invalid variable syntax: {token.value}", position=token.position)
            expr = match.group(1)
            parts = expr.split("|")
            var_name = parts[0]
            filters = parts[1:]
            children = _get_children(current)
            children.append(VarNode(name=var_name, filters=filters))

        elif token.type == "IF_OPEN":
            match = IF_PATTERN.match(token.value)
            if not match:
                raise TemplateSyntaxError(f"Invalid if syntax: {token.value}", position=token.position)
            condition = match.group(1).strip()
            if_node = IfNode(condition=condition)
            children = _get_children(current)
            children.append(if_node)
            stack.append(if_node)

        elif token.type == "ENDIF":
            if not isinstance(stack[-1], IfNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endif %}: no matching {% if %} block",
                    position=token.position,
                )
            stack.pop()

        elif token.type == "FOR_OPEN":
            match = FOR_PATTERN.match(token.value)
            if not match:
                raise TemplateSyntaxError(f"Invalid for syntax: {token.value}", position=token.position)
            var_name = match.group(1)
            iterable_name = match.group(2)
            for_node = ForNode(var_name=var_name, iterable_name=iterable_name)
            children = _get_children(current)
            children.append(for_node)
            stack.append(for_node)

        elif token.type == "ENDFOR":
            if not isinstance(stack[-1], ForNode):
                raise TemplateSyntaxError(
                    "Unexpected {% endfor %}: no matching {% for %} block",
                    position=token.position,
                )
            stack.pop()

    if len(stack) != 1:
        top = stack[-1]
        if isinstance(top, IfNode):
            raise TemplateSyntaxError("Unclosed {% if %} block")
        elif isinstance(top, ForNode):
            raise TemplateSyntaxError("Unclosed {% for %} block")
        else:
            raise TemplateSyntaxError("Unclosed template block")

    return root


def _get_children(node: BlockNode | IfNode | ForNode) -> list[Node]:
    if isinstance(node, BlockNode):
        return node.children
    elif isinstance(node, IfNode):
        return node.body
    elif isinstance(node, ForNode):
        return node.body
    raise TemplateSyntaxError("Invalid node type on stack")


# ---- Renderer ----

def render(node: Node, context: dict[str, Any]) -> str:
    if isinstance(node, TextNode):
        return node.content

    elif isinstance(node, VarNode):
        value = context.get(node.name, "")
        result = str(value)
        for filter_name in node.filters:
            if filter_name not in FILTERS:
                raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")
            result = FILTERS[filter_name](result)
        return result

    elif isinstance(node, IfNode):
        condition_value = context.get(node.condition)
        if condition_value:
            return "".join(render(child, context) for child in node.body)
        return ""

    elif isinstance(node, ForNode):
        iterable = context.get(node.iterable_name)
        if iterable is None:
            return ""
        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(
                f"Value '{node.iterable_name}' is not iterable"
            )
        parts: list[str] = []
        for item in iterable:
            child_context = {**context, node.var_name: item}
            for child in node.body:
                parts.append(render(child, child_context))
        return "".join(parts)

    elif isinstance(node, BlockNode):
        return "".join(render(child, context) for child in node.children)

    return ""


# ---- Template Engine ----

class TemplateEngine:
    def __init__(self) -> None:
        self.filters: dict[str, Callable[[str], str]] = dict(FILTERS)

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        self.filters[name] = fn
        FILTERS[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        tokens = tokenize(template)
        ast = parse(tokens)
        return render(ast, context)

    def parse(self, template: str) -> BlockNode:
        tokens = tokenize(template)
        return parse(tokens)


# ---- Demo ----

if __name__ == "__main__":
    engine = TemplateEngine()

    # Variable substitution
    result = engine.render("Hello, {{name}}!", {"name": "World"})
    print(f"1. {result}")

    # Filters
    result = engine.render("Hello, {{name|upper}}!", {"name": "world"})
    print(f"2. {result}")

    # Chained filters
    result = engine.render("{{name|upper|capitalize}}", {"name": "hello"})
    print(f"3. {result}")

    # Conditionals
    template = "{% if show_greeting %}Hello, {{name}}!{% endif %}"
    result = engine.render(template, {"show_greeting": True, "name": "Alice"})
    print(f"4. {result}")

    result = engine.render(template, {"show_greeting": False, "name": "Alice"})
    print(f"5. '{result}'")

    # Loops
    template = "Items: {% for item in items %}{{item}}, {% endfor %}"
    result = engine.render(template, {"items": ["apple", "banana", "cherry"]})
    print(f"6. {result}")

    # Nested structures
    template = """{% if show_list %}List:
{% for item in items %}  - {{item|upper}}
{% endfor %}{% endif %}"""
    result = engine.render(template, {"show_list": True, "items": ["a", "b", "c"]})
    print(f"7. {result}")

    # Error handling
    try:
        engine.render("{% if x %}no endif", {"x": True})
    except TemplateSyntaxError as e:
        print(f"8. Error caught: {e}")

    try:
        engine.render("{{name|nonexistent}}", {"name": "test"})
    except TemplateSyntaxError as e:
        print(f"9. Error caught: {e}")
