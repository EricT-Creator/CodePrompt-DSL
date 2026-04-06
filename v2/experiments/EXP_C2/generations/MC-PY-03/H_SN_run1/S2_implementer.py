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
    def __init__(self, var_name: str, iterable: str) -> None:
        self.var_name = var_name
        self.iterable = iterable
        self.children: list[Node] = []


_RE_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RE_IF_OPEN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RE_IF_CLOSE = re.compile(r"\{%\s*endif\s*%\}")
_RE_FOR_OPEN = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RE_FOR_CLOSE = re.compile(r"\{%\s*endfor\s*%\}")
_RE_TOKEN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RE_COMPARE = re.compile(r"^(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._filter_registry: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filter_registry[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        raw_tokens = [t for t in _RE_TOKEN.split(template) if t]
        ast = self._build_ast(raw_tokens)
        return self._render_ast(ast, context)

    def _build_ast(self, tokens: list[str]) -> list[Node]:
        root: list[Node] = []
        stack: list[tuple[IfNode | ForNode, list[Node]]] = []
        current = root

        for token in tokens:
            if m := _RE_VAR.fullmatch(token):
                segments = m.group(1).split("|")
                current.append(VarNode(segments[0], segments[1:]))
            elif m := _RE_IF_OPEN.fullmatch(token):
                node = IfNode(m.group(1))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif _RE_IF_CLOSE.fullmatch(token):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                popped, parent = stack.pop()
                if not isinstance(popped, IfNode):
                    raise TemplateSyntaxError("Unexpected endif — expected endfor")
                current = parent
            elif m := _RE_FOR_OPEN.fullmatch(token):
                node = ForNode(m.group(1), m.group(2))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif _RE_FOR_CLOSE.fullmatch(token):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                popped, parent = stack.pop()
                if not isinstance(popped, ForNode):
                    raise TemplateSyntaxError("Unexpected endfor — expected endif")
                current = parent
            elif token:
                current.append(TextNode(token))

        if stack:
            unclosed = stack[-1][0]
            label = "if" if isinstance(unclosed, IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {label} block")
        return root

    def _render_ast(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        output: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                output.append(node.content)
            elif isinstance(node, VarNode):
                output.append(self._resolve_var(node, ctx))
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, ctx):
                    output.append(self._render_ast(node.children, ctx))
            elif isinstance(node, ForNode):
                collection = ctx.get(node.iterable, [])
                for element in collection:
                    child_ctx = {**ctx, node.var_name: element}
                    output.append(self._render_ast(node.children, child_ctx))
        return "".join(output)

    def _resolve_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        raw = ctx.get(node.name, "")
        result = str(raw)
        for filter_name in node.filters:
            if filter_name not in self._filter_registry:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            result = self._filter_registry[filter_name](result)
        return result

    def _evaluate_condition(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        if m := _RE_COMPARE.match(cond):
            left = str(ctx.get(m.group(1), ""))
            operator = m.group(2)
            right = m.group(3).strip().strip("\"'")
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
            try:
                lf, rf = float(left), float(right)
            except ValueError:
                return False
            if operator == ">":
                return lf > rf
            if operator == "<":
                return lf < rf
            if operator == ">=":
                return lf >= rf
            if operator == "<=":
                return lf <= rf
        return bool(ctx.get(cond, False))
