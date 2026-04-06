from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

TOKEN_PATTERN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)


class TemplateSyntaxError(Exception):
    pass


@dataclass
class TextNode:
    text: str


@dataclass
class VariableNode:
    expression: str


@dataclass
class IfNode:
    condition: str
    children: list[Any]


@dataclass
class ForNode:
    variable_name: str
    iterable_expression: str
    children: list[Any]


Node = TextNode | VariableNode | IfNode | ForNode


def tokenize(template: str) -> list[str]:
    return [part for part in TOKEN_PATTERN.split(template) if part]


def parse(template: str) -> list[Node]:
    tokens = tokenize(template)
    nodes, index = _parse_block(tokens, 0, ())
    if index != len(tokens):
        raise TemplateSyntaxError("Unexpected trailing tokens")
    return nodes


def _parse_block(tokens: list[str], index: int, stop_tags: tuple[str, ...]) -> tuple[list[Node], int]:
    nodes: list[Node] = []

    while index < len(tokens):
        token = tokens[index]

        if token.startswith("{{"):
            expression = token[2:-2].strip()
            if not expression:
                raise TemplateSyntaxError("Empty variable expression")
            nodes.append(VariableNode(expression))
            index += 1
            continue

        if token.startswith("{%"):
            statement = token[2:-2].strip()
            if statement in stop_tags:
                return nodes, index

            if statement.startswith("if "):
                condition = statement[3:].strip()
                if not condition:
                    raise TemplateSyntaxError("If tag requires a condition")
                children, next_index = _parse_block(tokens, index + 1, ("endif",))
                if next_index >= len(tokens) or tokens[next_index][2:-2].strip() != "endif":
                    raise TemplateSyntaxError("Missing endif tag")
                nodes.append(IfNode(condition, children))
                index = next_index + 1
                continue

            if statement.startswith("for "):
                match = re.fullmatch(r"for\s+([A-Za-z_]\w*)\s+in\s+(.+)", statement)
                if not match:
                    raise TemplateSyntaxError("Malformed for tag")
                variable_name, iterable_expression = match.groups()
                children, next_index = _parse_block(tokens, index + 1, ("endfor",))
                if next_index >= len(tokens) or tokens[next_index][2:-2].strip() != "endfor":
                    raise TemplateSyntaxError("Missing endfor tag")
                nodes.append(ForNode(variable_name, iterable_expression.strip(), children))
                index = next_index + 1
                continue

            if statement in {"endif", "endfor"}:
                raise TemplateSyntaxError(f"Unexpected closing tag: {statement}")

            raise TemplateSyntaxError(f"Unknown tag: {statement}")

        nodes.append(TextNode(token))
        index += 1

    if stop_tags:
        raise TemplateSyntaxError(f"Missing closing tag for {', '.join(stop_tags)}")
    return nodes, index


def resolve_path(expression: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in expression.split("."):
        key = part.strip()
        if not key:
            raise TemplateSyntaxError(f"Invalid path: {expression}")
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current


def parse_literal(token: str) -> Any:
    if token in {"True", "true"}:
        return True
    if token in {"False", "false"}:
        return False
    if token in {"None", "none", "null"}:
        return None
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    if (token.startswith("\"") and token.endswith("\"")) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    return resolve_path(token, {})


def evaluate_atom(token: str, context: dict[str, Any]) -> Any:
    token = token.strip()
    if not token:
        raise TemplateSyntaxError("Empty expression")
    if token in {"True", "true", "False", "false", "None", "none", "null"}:
        return parse_literal(token)
    if re.fullmatch(r"-?\d+(?:\.\d+)?", token):
        return parse_literal(token)
    if (token.startswith("\"") and token.endswith("\"")) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    return resolve_path(token, context)


FILTERS = {
    "upper": lambda value: "" if value is None else str(value).upper(),
    "lower": lambda value: "" if value is None else str(value).lower(),
    "title": lambda value: "" if value is None else str(value).title(),
}


def evaluate_expression(expression: str, context: dict[str, Any]) -> Any:
    parts = [part.strip() for part in expression.split("|")]
    if not parts or not parts[0]:
        raise TemplateSyntaxError("Empty expression")

    value = evaluate_atom(parts[0], context)
    for filter_name in parts[1:]:
        if filter_name not in FILTERS:
            raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
        value = FILTERS[filter_name](value)
    return value


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    stripped = condition.strip()
    if stripped.startswith("not "):
        return not evaluate_condition(stripped[4:], context)

    for operator in ("==", "!="):
        if operator in stripped:
            left, right = stripped.split(operator, 1)
            left_value = evaluate_atom(left.strip(), context)
            right_value = evaluate_atom(right.strip(), context)
            return left_value == right_value if operator == "==" else left_value != right_value

    return bool(evaluate_expression(stripped, context))


def render_nodes(nodes: list[Node], context: dict[str, Any]) -> str:
    output: list[str] = []

    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.text)
            continue

        if isinstance(node, VariableNode):
            value = evaluate_expression(node.expression, context)
            output.append("" if value is None else str(value))
            continue

        if isinstance(node, IfNode):
            if evaluate_condition(node.condition, context):
                output.append(render_nodes(node.children, context))
            continue

        if isinstance(node, ForNode):
            iterable = evaluate_expression(node.iterable_expression, context)
            if iterable is None:
                continue
            try:
                iterator = list(iterable)
            except TypeError as exc:
                raise TemplateSyntaxError("For loop target is not iterable") from exc

            for item in iterator:
                nested_context = dict(context)
                nested_context[node.variable_name] = item
                output.append(render_nodes(node.children, nested_context))
            continue

        raise TemplateSyntaxError("Unsupported node encountered")

    return "".join(output)


def render(template: str, context: dict[str, Any]) -> str:
    nodes = parse(template)
    return render_nodes(nodes, dict(context))


if __name__ == "__main__":
    sample = "Hello {{ user.name|title }}! {% if items %}{% for item in items %}[{{ item|upper }}]{% endfor %}{% endif %}"
    data = {"user": {"name": "eric"}, "items": ["alpha", "beta"]}
    print(render(sample, data))
