import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


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
    body: List[Any]


@dataclass
class ForNode:
    variable_name: str
    iterable_name: str
    body: List[Any]


TOKEN_PATTERN = re.compile(r"({{.*?}}|{%.*?%})", re.DOTALL)
FOR_PATTERN = re.compile(r"^for\s+(\w+)\s+in\s+([\w\.]+)$")


def _tokenize(template: str) -> List[str]:
    parts = TOKEN_PATTERN.split(template)
    return [part for part in parts if part != ""]


def _parse(tokens: Sequence[str], start: int = 0, stop_tags: Tuple[str, ...] = ()):
    nodes: List[Any] = []
    index = start

    while index < len(tokens):
        token = tokens[index]
        if token.startswith("{{"):
            expression = token[2:-2].strip()
            if not expression:
                raise TemplateSyntaxError("Empty variable tag")
            nodes.append(VariableNode(expression))
            index += 1
            continue

        if token.startswith("{%"):
            tag = token[2:-2].strip()
            if tag in stop_tags:
                return nodes, index, tag

            if tag.startswith("if "):
                condition = tag[3:].strip()
                if not condition:
                    raise TemplateSyntaxError("If block requires a condition")
                body, next_index, stop_tag = _parse(tokens, index + 1, ("endif",))
                if stop_tag != "endif":
                    raise TemplateSyntaxError("Missing endif tag")
                nodes.append(IfNode(condition, body))
                index = next_index + 1
                continue

            if tag.startswith("for "):
                match = FOR_PATTERN.match(tag)
                if not match:
                    raise TemplateSyntaxError("Malformed for tag")
                variable_name, iterable_name = match.groups()
                body, next_index, stop_tag = _parse(tokens, index + 1, ("endfor",))
                if stop_tag != "endfor":
                    raise TemplateSyntaxError("Missing endfor tag")
                nodes.append(ForNode(variable_name, iterable_name, body))
                index = next_index + 1
                continue

            if tag in {"endif", "endfor"}:
                raise TemplateSyntaxError(f"Unexpected closing tag: {tag}")

            raise TemplateSyntaxError(f"Unknown tag: {tag}")

        nodes.append(TextNode(token))
        index += 1

    if stop_tags:
        raise TemplateSyntaxError(f"Missing closing tag for {' or '.join(stop_tags)}")

    return nodes, index, None


def _resolve(name: str, context: Dict[str, Any]) -> Any:
    parts = [part for part in name.split(".") if part]
    if not parts:
        raise TemplateSyntaxError("Empty expression")

    value: Any = context
    for part in parts:
        if isinstance(value, dict):
            if part not in value:
                raise TemplateSyntaxError(f"Unknown variable: {name}")
            value = value[part]
        else:
            if not hasattr(value, part):
                raise TemplateSyntaxError(f"Unknown attribute: {name}")
            value = getattr(value, part)
    return value


def _evaluate_condition(expression: str, context: Dict[str, Any]) -> bool:
    expression = expression.strip()
    if expression.startswith("not "):
        return not bool(_resolve(expression[4:].strip(), context))
    return bool(_resolve(expression, context))


def _apply_filters(value: Any, filters: List[str]) -> Any:
    for filter_name in filters:
        if filter_name == "upper":
            value = str(value).upper()
        elif filter_name == "lower":
            value = str(value).lower()
        elif filter_name == "title":
            value = str(value).title()
        else:
            raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
    return value


def _render_nodes(nodes: Sequence[Any], context: Dict[str, Any]) -> str:
    output: List[str] = []

    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.text)
        elif isinstance(node, VariableNode):
            parts = [part.strip() for part in node.expression.split("|")]
            value = _resolve(parts[0], context)
            value = _apply_filters(value, parts[1:])
            output.append(str(value))
        elif isinstance(node, IfNode):
            if _evaluate_condition(node.condition, context):
                output.append(_render_nodes(node.body, context))
        elif isinstance(node, ForNode):
            iterable = _resolve(node.iterable_name, context)
            try:
                iterator = list(iterable)
            except TypeError as exc:
                raise TemplateSyntaxError(f"Value is not iterable: {node.iterable_name}") from exc
            for item in iterator:
                child_context = dict(context)
                child_context[node.variable_name] = item
                output.append(_render_nodes(node.body, child_context))
        else:
            raise TemplateSyntaxError("Unsupported node encountered")

    return "".join(output)


def render(template_string: str, context_dict: Dict[str, Any]) -> str:
    tokens = _tokenize(template_string)
    nodes, index, stop_tag = _parse(tokens)
    if stop_tag is not None or index != len(tokens):
        raise TemplateSyntaxError("Unexpected trailing template content")
    return _render_nodes(nodes, dict(context_dict))


if __name__ == "__main__":
    template = "Hello {{ user.name|title }}! {% if user.active %}{% for item in items %}{{ item|upper }} {% endfor %}{% endif %}"
    context = {"user": {"name": "eric", "active": True}, "items": ["alpha", "beta"]}
    print(render(template, context))
