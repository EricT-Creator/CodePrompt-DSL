import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

TOKEN_PATTERN = re.compile(r"({{.*?}}|{%\s*.*?%})", re.S)
FOR_PATTERN = re.compile(r"^for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.+)$")


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
    true_branch: List[Any]
    false_branch: List[Any]


@dataclass
class ForNode:
    variable_name: str
    iterable_expression: str
    body: List[Any]


Node = Any


def tokenize(template: str) -> List[Tuple[str, str]]:
    tokens: List[Tuple[str, str]] = []
    cursor = 0
    for match in TOKEN_PATTERN.finditer(template):
        start, end = match.span()
        if start > cursor:
            tokens.append(("text", template[cursor:start]))
        token = match.group(0)
        if token.startswith("{{"):
            tokens.append(("variable", token[2:-2].strip()))
        else:
            tokens.append(("tag", token[2:-2].strip()))
        cursor = end
    if cursor < len(template):
        tokens.append(("text", template[cursor:]))
    return tokens


def parse(template: str) -> List[Node]:
    tokens = tokenize(template)
    nodes, index, closing = parse_block(tokens, 0, None)
    if closing is not None:
        raise TemplateSyntaxError(f"Unexpected closing tag: {closing}")
    if index != len(tokens):
        raise TemplateSyntaxError("Template parsing ended unexpectedly")
    return nodes


def parse_block(
    tokens: Sequence[Tuple[str, str]],
    start_index: int,
    expected_end_tags: Optional[Sequence[str]],
) -> Tuple[List[Node], int, Optional[str]]:
    nodes: List[Node] = []
    index = start_index
    expected = set(expected_end_tags or [])

    while index < len(tokens):
        token_type, token_value = tokens[index]
        if token_type == "text":
            nodes.append(TextNode(token_value))
            index += 1
            continue

        if token_type == "variable":
            if not token_value:
                raise TemplateSyntaxError("Empty variable expression")
            nodes.append(VariableNode(token_value))
            index += 1
            continue

        if token_value in {"endif", "endfor", "else"}:
            if token_value in expected:
                return nodes, index, token_value
            raise TemplateSyntaxError(f"Unexpected tag: {token_value}")

        if token_value.startswith("if "):
            condition = token_value[3:].strip()
            if not condition:
                raise TemplateSyntaxError("If tag requires a condition")
            true_branch, index, closing = parse_block(tokens, index + 1, ["else", "endif"])
            false_branch: List[Node] = []

            if closing == "else":
                false_branch, index, closing = parse_block(tokens, index + 1, ["endif"])

            if closing != "endif":
                raise TemplateSyntaxError("Missing endif tag")

            nodes.append(IfNode(condition=condition, true_branch=true_branch, false_branch=false_branch))
            index += 1
            continue

        if token_value.startswith("for "):
            match = FOR_PATTERN.match(token_value)
            if not match:
                raise TemplateSyntaxError(f"Invalid for syntax: {token_value}")
            variable_name, iterable_expression = match.groups()
            body, index, closing = parse_block(tokens, index + 1, ["endfor"])
            if closing != "endfor":
                raise TemplateSyntaxError("Missing endfor tag")
            nodes.append(
                ForNode(
                    variable_name=variable_name,
                    iterable_expression=iterable_expression.strip(),
                    body=body,
                )
            )
            index += 1
            continue

        raise TemplateSyntaxError(f"Unknown template tag: {token_value}")

    if expected:
        raise TemplateSyntaxError(f"Missing closing tag: {', '.join(expected)}")
    return nodes, index, None


def resolve_name(expression: str, context: Dict[str, Any]) -> Any:
    current: Any = context
    for part in expression.split("."):
        key = part.strip()
        if not key:
            raise TemplateSyntaxError(f"Invalid expression: {expression}")
        if isinstance(current, dict):
            if key not in current:
                return ""
            current = current[key]
        else:
            current = getattr(current, key, "")
    return current


def apply_filters(value: Any, filters: Sequence[str]) -> Any:
    result = value
    for filter_name in filters:
        if filter_name == "upper":
            result = str(result).upper()
        elif filter_name == "lower":
            result = str(result).lower()
        elif filter_name == "title":
            result = str(result).title()
        else:
            raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
    return result


def evaluate_expression(expression: str, context: Dict[str, Any]) -> Any:
    parts = [part.strip() for part in expression.split("|")]
    if not parts or not parts[0]:
        raise TemplateSyntaxError("Invalid expression")
    value = resolve_name(parts[0], context)
    return apply_filters(value, parts[1:])


def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    stripped = condition.strip()
    if stripped.startswith("not "):
        return not bool(evaluate_expression(stripped[4:].strip(), context))
    return bool(evaluate_expression(stripped, context))


def render_nodes(nodes: Sequence[Node], context: Dict[str, Any]) -> str:
    output: List[str] = []
    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.value)
        elif isinstance(node, VariableNode):
            output.append(str(evaluate_expression(node.expression, context)))
        elif isinstance(node, IfNode):
            branch = node.true_branch if evaluate_condition(node.condition, context) else node.false_branch
            output.append(render_nodes(branch, context))
        elif isinstance(node, ForNode):
            iterable = evaluate_expression(node.iterable_expression, context)
            if iterable is None:
                continue
            if not isinstance(iterable, (list, tuple, set)):
                raise TemplateSyntaxError("For loop iterable must resolve to a list, tuple, or set")
            for item in iterable:
                child_context = dict(context)
                child_context[node.variable_name] = item
                output.append(render_nodes(node.body, child_context))
        else:
            raise TemplateSyntaxError(f"Unknown node type: {type(node).__name__}")
    return "".join(output)


def render(template: str, context: Dict[str, Any]) -> str:
    nodes = parse(template)
    return render_nodes(nodes, dict(context))


if __name__ == "__main__":
    sample = """
Hello {{ user.name|title }}!
{% if items %}
Items:
{% for item in items %}- {{ item|upper }}
{% endfor %}
{% else %}
No items available.
{% endif %}
""".strip()

    print(
        render(
            sample,
            {
                "user": {"name": "ada lovelace"},
                "items": ["notes", "experiments", "reports"],
            },
        )
    )
