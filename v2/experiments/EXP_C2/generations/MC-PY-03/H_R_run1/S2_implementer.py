from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    pass


class Node:
    pass


class TextNode(Node):
    def __init__(self, content: str) -> None:
        self.content = content


class VarNode(Node):
    def __init__(self, name: str, filters: list[str]) -> None:
        self.name = name
        self.filters = filters


class IfNode(Node):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.children: list[Node] = []


class ForNode(Node):
    def __init__(self, var_name: str, iterable_name: str) -> None:
        self.var_name = var_name
        self.iterable_name = iterable_name
        self.children: list[Node] = []


_VAR_RE = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF_OPEN_RE = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_IF_CLOSE_RE = re.compile(r"\{%\s*endif\s*%\}")
_FOR_OPEN_RE = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_FOR_CLOSE_RE = re.compile(r"\{%\s*endfor\s*%\}")
_TOKEN_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")

_CMP_RE = re.compile(r"^(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        tokens = self._tokenize(template)
        ast = self._parse(tokens)
        return self._render_nodes(ast, context)

    def _tokenize(self, template: str) -> list[str]:
        parts = _TOKEN_RE.split(template)
        return [p for p in parts if p]

    def _parse(self, tokens: list[str]) -> list[Node]:
        root: list[Node] = []
        stack: list[tuple[Node, list[Node]]] = []
        current: list[Node] = root

        for token in tokens:
            m_var = _VAR_RE.fullmatch(token)
            m_if = _IF_OPEN_RE.fullmatch(token)
            m_endif = _IF_CLOSE_RE.fullmatch(token)
            m_for = _FOR_OPEN_RE.fullmatch(token)
            m_endfor = _FOR_CLOSE_RE.fullmatch(token)

            if m_var:
                parts = m_var.group(1).split("|")
                name = parts[0]
                filters = parts[1:]
                current.append(VarNode(name, filters))
            elif m_if:
                node = IfNode(m_if.group(1))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif m_endif:
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top_node, parent = stack.pop()
                if not isinstance(top_node, IfNode):
                    raise TemplateSyntaxError("Unexpected endif — expected endfor")
                current = parent
            elif m_for:
                node = ForNode(m_for.group(1), m_for.group(2))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif m_endfor:
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top_node, parent = stack.pop()
                if not isinstance(top_node, ForNode):
                    raise TemplateSyntaxError("Unexpected endfor — expected endif")
                current = parent
            else:
                if token:
                    current.append(TextNode(token))

        if stack:
            top = stack[-1][0]
            kind = "if" if isinstance(top, IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")

        return root

    def _render_nodes(self, nodes: list[Node], context: dict[str, Any]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                parts.append(node.content)
            elif isinstance(node, VarNode):
                parts.append(self._render_var(node, context))
            elif isinstance(node, IfNode):
                if self._eval_condition(node.condition, context):
                    parts.append(self._render_nodes(node.children, context))
            elif isinstance(node, ForNode):
                iterable = context.get(node.iterable_name, [])
                if not hasattr(iterable, "__iter__"):
                    iterable = []
                for item in iterable:
                    child_ctx = {**context, node.var_name: item}
                    parts.append(self._render_nodes(node.children, child_ctx))
        return "".join(parts)

    def _render_var(self, node: VarNode, context: dict[str, Any]) -> str:
        value = context.get(node.name, "")
        result = str(value)
        for f_name in node.filters:
            if f_name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {f_name}")
            result = self._filters[f_name](result)
        return result

    def _eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        condition = condition.strip()
        m = _CMP_RE.match(condition)
        if m:
            var_name = m.group(1)
            op = m.group(2)
            rhs_raw = m.group(3).strip().strip("\"'")
            lhs = str(context.get(var_name, ""))
            if op == "==":
                return lhs == rhs_raw
            elif op == "!=":
                return lhs != rhs_raw
            elif op == ">":
                try:
                    return float(lhs) > float(rhs_raw)
                except ValueError:
                    return lhs > rhs_raw
            elif op == "<":
                try:
                    return float(lhs) < float(rhs_raw)
                except ValueError:
                    return lhs < rhs_raw
            elif op == ">=":
                try:
                    return float(lhs) >= float(rhs_raw)
                except ValueError:
                    return lhs >= rhs_raw
            elif op == "<=":
                try:
                    return float(lhs) <= float(rhs_raw)
                except ValueError:
                    return lhs <= rhs_raw
        return bool(context.get(condition, False))
