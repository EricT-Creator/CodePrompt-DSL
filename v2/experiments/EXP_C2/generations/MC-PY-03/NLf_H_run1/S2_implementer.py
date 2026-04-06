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


_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_TOK = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_CMP = re.compile(r"^(\w+)\s*(==|!=|>=?|<=?)\s*(.+)$")


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
        parts = [p for p in _TOK.split(template) if p]
        nodes = self._parse(parts)
        return self._render_nodes(nodes, context)

    def _parse(self, tokens: list[str]) -> list[Node]:
        root: list[Node] = []
        stack: list[tuple[Node, list[Node]]] = []
        active = root

        for t in tokens:
            if m := _VAR.fullmatch(t):
                segs = m.group(1).split("|")
                active.append(VarNode(segs[0], segs[1:]))
            elif m := _IF.fullmatch(t):
                n = IfNode(m.group(1))
                active.append(n)
                stack.append((n, active))
                active = n.children
            elif _ENDIF.fullmatch(t):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, prev = stack.pop()
                if not isinstance(top, IfNode):
                    raise TemplateSyntaxError("Mismatched endif")
                active = prev
            elif m := _FOR.fullmatch(t):
                n = ForNode(m.group(1), m.group(2))
                active.append(n)
                stack.append((n, active))
                active = n.children
            elif _ENDFOR.fullmatch(t):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, prev = stack.pop()
                if not isinstance(top, ForNode):
                    raise TemplateSyntaxError("Mismatched endfor")
                active = prev
            elif t:
                active.append(TextNode(t))

        if stack:
            tp = "if" if isinstance(stack[-1][0], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {tp} block")
        return root

    def _render_nodes(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        out: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                out.append(node.content)
            elif isinstance(node, VarNode):
                v = str(ctx.get(node.name, ""))
                for fn in node.filters:
                    if fn not in self._filters:
                        raise TemplateSyntaxError(f"Unknown filter: {fn}")
                    v = self._filters[fn](v)
                out.append(v)
            elif isinstance(node, IfNode):
                if self._test(node.condition, ctx):
                    out.append(self._render_nodes(node.children, ctx))
            elif isinstance(node, ForNode):
                items = ctx.get(node.iterable_name, [])
                for el in items:
                    out.append(self._render_nodes(node.children, {**ctx, node.var_name: el}))
        return "".join(out)

    def _test(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        if m := _CMP.match(cond):
            left = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            right = m.group(3).strip().strip("\"'")
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            try:
                lf, rf = float(left), float(right)
            except ValueError:
                return False
            if op == ">":
                return lf > rf
            if op == "<":
                return lf < rf
            if op == ">=":
                return lf >= rf
            if op == "<=":
                return lf <= rf
        return bool(ctx.get(cond, False))
