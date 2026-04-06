from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class TemplateSyntaxError(Exception):
    pass


_VAR_PATTERN = re.compile(r'\{\{(.+?)\}\}')
_BLOCK_PATTERN = re.compile(
    r'\{%\s*(if|elif|else|endif|for|endfor)\s*(.*?)\s*%\}'
)


def _apply_filter(value: Any, filter_name: str) -> str:
    s = str(value)
    filters = {
        'upper': lambda v: v.upper(),
        'lower': lambda v: v.lower(),
        'title': lambda v: v.title(),
        'strip': lambda v: v.strip(),
        'capitalize': lambda v: v.capitalize(),
        'length': lambda v: str(len(v)),
    }
    if filter_name not in filters:
        raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")
    return filters[filter_name](s)


def _resolve_variable(expr: str, context: Dict[str, Any]) -> Any:
    expr = expr.strip()

    parts = [p.strip() for p in expr.split('|')]
    var_expr = parts[0]
    filter_names = parts[1:]

    value = _resolve_dotted(var_expr, context)

    for f in filter_names:
        value = _apply_filter(value, f)

    return value


def _resolve_dotted(expr: str, context: Dict[str, Any]) -> Any:
    parts = expr.split('.')
    value: Any = context

    for part in parts:
        if isinstance(value, dict):
            if part in value:
                value = value[part]
            else:
                return ''
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            return ''

    return value


def _evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    condition = condition.strip()

    not_match = re.match(r'^not\s+(.+)$', condition)
    if not_match:
        return not _evaluate_condition(not_match.group(1), context)

    and_parts = re.split(r'\s+and\s+', condition)
    if len(and_parts) > 1:
        return all(_evaluate_condition(p, context) for p in and_parts)

    or_parts = re.split(r'\s+or\s+', condition)
    if len(or_parts) > 1:
        return any(_evaluate_condition(p, context) for p in or_parts)

    comp_match = re.match(r'^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$', condition)
    if comp_match:
        left = _resolve_variable(comp_match.group(1), context)
        op = comp_match.group(2)
        right_str = comp_match.group(3).strip()

        if (right_str.startswith("'") and right_str.endswith("'")) or \
           (right_str.startswith('"') and right_str.endswith('"')):
            right: Any = right_str[1:-1]
        else:
            try:
                right = int(right_str)
            except ValueError:
                try:
                    right = float(right_str)
                except ValueError:
                    right = _resolve_variable(right_str, context)

        ops = {
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
        }
        try:
            return ops[op](left, right)
        except TypeError:
            return False

    value = _resolve_variable(condition, context)
    return bool(value)


class _Token:
    TEXT = 'text'
    VAR = 'var'
    BLOCK = 'block'

    def __init__(self, type_: str, content: str, tag: str = '', expr: str = ''):
        self.type = type_
        self.content = content
        self.tag = tag
        self.expr = expr


def _tokenize(template: str) -> List[_Token]:
    tokens: List[_Token] = []
    combined = re.compile(r'(\{\{.+?\}\}|\{%.+?%\})', re.DOTALL)
    parts = combined.split(template)

    for part in parts:
        if not part:
            continue
        if part.startswith('{{') and part.endswith('}}'):
            inner = part[2:-2].strip()
            if not inner:
                raise TemplateSyntaxError("Empty variable expression: {{}}")
            tokens.append(_Token(_Token.VAR, part, expr=inner))
        elif part.startswith('{%') and part.endswith('%}'):
            inner = part[2:-2].strip()
            match = re.match(r'^(if|elif|else|endif|for|endfor)\s*(.*)', inner)
            if not match:
                raise TemplateSyntaxError(f"Unknown block tag: {{% {inner} %}}")
            tag = match.group(1)
            expr = match.group(2).strip()
            tokens.append(_Token(_Token.BLOCK, part, tag=tag, expr=expr))
        else:
            tokens.append(_Token(_Token.TEXT, part))

    return tokens


class _Node:
    pass


class _TextNode(_Node):
    def __init__(self, text: str):
        self.text = text


class _VarNode(_Node):
    def __init__(self, expr: str):
        self.expr = expr


class _IfNode(_Node):
    def __init__(self):
        self.branches: List[tuple[Optional[str], List[_Node]]] = []


class _ForNode(_Node):
    def __init__(self, var_name: str, iterable_expr: str):
        self.var_name = var_name
        self.iterable_expr = iterable_expr
        self.body: List[_Node] = []


def _parse(tokens: List[_Token]) -> List[_Node]:
    nodes: List[_Node] = []
    pos = [0]

    def parse_nodes(stop_tags: tuple = ()) -> List[_Node]:
        result: List[_Node] = []
        while pos[0] < len(tokens):
            token = tokens[pos[0]]

            if token.type == _Token.TEXT:
                result.append(_TextNode(token.content))
                pos[0] += 1

            elif token.type == _Token.VAR:
                result.append(_VarNode(token.expr))
                pos[0] += 1

            elif token.type == _Token.BLOCK:
                if token.tag in stop_tags:
                    return result

                if token.tag == 'if':
                    node = _IfNode()
                    condition = token.expr
                    if not condition:
                        raise TemplateSyntaxError("{% if %} requires a condition")
                    pos[0] += 1
                    body = parse_nodes(('elif', 'else', 'endif'))

                    node.branches.append((condition, body))

                    while pos[0] < len(tokens) and tokens[pos[0]].tag == 'elif':
                        elif_cond = tokens[pos[0]].expr
                        if not elif_cond:
                            raise TemplateSyntaxError("{% elif %} requires a condition")
                        pos[0] += 1
                        elif_body = parse_nodes(('elif', 'else', 'endif'))
                        node.branches.append((elif_cond, elif_body))

                    if pos[0] < len(tokens) and tokens[pos[0]].tag == 'else':
                        pos[0] += 1
                        else_body = parse_nodes(('endif',))
                        node.branches.append((None, else_body))

                    if pos[0] >= len(tokens) or tokens[pos[0]].tag != 'endif':
                        raise TemplateSyntaxError("Missing {% endif %}")
                    pos[0] += 1
                    result.append(node)

                elif token.tag == 'for':
                    for_match = re.match(r'^(\w+)\s+in\s+(.+)$', token.expr)
                    if not for_match:
                        raise TemplateSyntaxError(
                            f"Invalid for syntax: {{% for {token.expr} %}}"
                        )
                    var_name = for_match.group(1)
                    iterable_expr = for_match.group(2).strip()
                    node = _ForNode(var_name, iterable_expr)
                    pos[0] += 1
                    node.body = parse_nodes(('endfor',))
                    if pos[0] >= len(tokens) or tokens[pos[0]].tag != 'endfor':
                        raise TemplateSyntaxError("Missing {% endfor %}")
                    pos[0] += 1
                    result.append(node)

                elif token.tag in ('endif', 'endfor', 'else', 'elif'):
                    raise TemplateSyntaxError(f"Unexpected {{% {token.tag} %}}")

                else:
                    raise TemplateSyntaxError(f"Unknown tag: {token.tag}")
            else:
                pos[0] += 1

        return result

    nodes = parse_nodes()
    return nodes


def _render_nodes(nodes: List[_Node], context: Dict[str, Any]) -> str:
    output: List[str] = []

    for node in nodes:
        if isinstance(node, _TextNode):
            output.append(node.text)

        elif isinstance(node, _VarNode):
            value = _resolve_variable(node.expr, context)
            output.append(str(value) if value is not None else '')

        elif isinstance(node, _IfNode):
            rendered = False
            for condition, body in node.branches:
                if condition is None:
                    output.append(_render_nodes(body, context))
                    rendered = True
                    break
                if _evaluate_condition(condition, context):
                    output.append(_render_nodes(body, context))
                    rendered = True
                    break

        elif isinstance(node, _ForNode):
            iterable = _resolve_variable(node.iterable_expr, context)
            if iterable and hasattr(iterable, '__iter__'):
                for item in iterable:
                    child_context = {**context, node.var_name: item}
                    output.append(_render_nodes(node.body, child_context))

    return ''.join(output)


def render(template_string: str, context_dict: Dict[str, Any]) -> str:
    tokens = _tokenize(template_string)
    tree = _parse(tokens)
    return _render_nodes(tree, context_dict)


if __name__ == "__main__":
    template = """
Hello, {{ name|upper }}!

{% if show_items %}
Your items:
{% for item in items %}
  - {{ item|title }}
{% endfor %}
{% endif %}

{% if score > 90 %}
Grade: A
{% elif score > 70 %}
Grade: B
{% else %}
Grade: C
{% endif %}

Goodbye, {{ name|lower }}!
"""

    ctx = {
        "name": "alice",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
        "score": 85,
    }

    print(render(template, ctx))
