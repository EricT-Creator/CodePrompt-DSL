import re
from dataclasses import dataclass
from typing import Any

TOKEN_PATTERN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)
VARIABLE_PATTERN = re.compile(r"^\{\{\s*(.*?)\s*\}\}$", re.DOTALL)
BLOCK_PATTERN = re.compile(r"^\{%\s*(.*?)\s*%\}$", re.DOTALL)
FOR_PATTERN = re.compile(r"^for\s+(\w+)\s+in\s+([\w.]+)$")


class TemplateSyntaxError(Exception):
    pass


@dataclass
class TextNode:
    value: str


@dataclass
class VariableNode:
    expression: str


@dataclass
class IfNode:
    condition: str
    body: list[Any]


@dataclass
class ForNode:
    variable_name: str
    iterable_name: str
    body: list[Any]


Node = TextNode | VariableNode | IfNode | ForNode


def resolve_name(name: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in name.split('.'):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def apply_filters(value: Any, filters: list[str]) -> str:
    text = "" if value is None else str(value)
    for filter_name in filters:
        if filter_name == "upper":
            text = text.upper()
        elif filter_name == "lower":
            text = text.lower()
        elif filter_name == "title":
            text = text.title()
        else:
            raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
    return text


def tokenize(template: str) -> list[str]:
    parts = TOKEN_PATTERN.split(template)
    return [part for part in parts if part != ""]


def parse_nodes(tokens: list[str], start_index: int = 0, stop_tags: tuple[str, ...] = ()) -> tuple[list[Node], int]:
    nodes: list[Node] = []
    index = start_index

    while index < len(tokens):
        token = tokens[index]
        variable_match = VARIABLE_PATTERN.match(token)
        block_match = BLOCK_PATTERN.match(token)

        if variable_match:
            nodes.append(VariableNode(variable_match.group(1).strip()))
            index += 1
            continue

        if block_match:
            block_content = block_match.group(1).strip()
            if block_content in stop_tags:
                return nodes, index
            if block_content.startswith("if "):
                body, next_index = parse_nodes(tokens, index + 1, ("endif",))
                if next_index >= len(tokens):
                    raise TemplateSyntaxError("Missing endif")
                nodes.append(IfNode(block_content[3:].strip(), body))
                index = next_index + 1
                continue
            if block_content.startswith("for "):
                loop_match = FOR_PATTERN.match(block_content)
                if not loop_match:
                    raise TemplateSyntaxError(f"Invalid for syntax: {block_content}")
                body, next_index = parse_nodes(tokens, index + 1, ("endfor",))
                if next_index >= len(tokens):
                    raise TemplateSyntaxError("Missing endfor")
                nodes.append(ForNode(loop_match.group(1), loop_match.group(2), body))
                index = next_index + 1
                continue
            if block_content in {"endif", "endfor"}:
                raise TemplateSyntaxError(f"Unexpected block close: {block_content}")
            raise TemplateSyntaxError(f"Unknown block tag: {block_content}")

        nodes.append(TextNode(token))
        index += 1

    if stop_tags:
        raise TemplateSyntaxError(f"Missing closing tag for: {', '.join(stop_tags)}")
    return nodes, index


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    condition = condition.strip()
    if condition.startswith("not "):
        return not bool(resolve_name(condition[4:].strip(), context))
    return bool(resolve_name(condition, context))


def render_nodes(nodes: list[Node], context: dict[str, Any]) -> str:
    output: list[str] = []
    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.value)
        elif isinstance(node, VariableNode):
            segments = [segment.strip() for segment in node.expression.split("|")]
            base_name = segments[0]
            filters = segments[1:]
            output.append(apply_filters(resolve_name(base_name, context), filters))
        elif isinstance(node, IfNode):
            if evaluate_condition(node.condition, context):
                output.append(render_nodes(node.body, context))
        elif isinstance(node, ForNode):
            iterable = resolve_name(node.iterable_name, context)
            if iterable is None:
                continue
            for item in iterable:
                nested_context = dict(context)
                nested_context[node.variable_name] = item
                output.append(render_nodes(node.body, nested_context))
        else:
            raise TemplateSyntaxError("Unsupported node type")
    return "".join(output)


def render(template: str, context: dict[str, Any]) -> str:
    tokens = tokenize(template)
    nodes, index = parse_nodes(tokens)
    if index != len(tokens):
        raise TemplateSyntaxError("Unexpected trailing template content")
    return render_nodes(nodes, dict(context))


if __name__ == "__main__":
    sample = "Hello {{ user.name|title }}! {% if user.active %}{% for item in items %}- {{ item|upper }} {% endfor %}{% endif %}"
    data = {"user": {"name": "erichztang", "active": True}, "items": ["alpha", "beta"]}
    print(render(sample, data))
