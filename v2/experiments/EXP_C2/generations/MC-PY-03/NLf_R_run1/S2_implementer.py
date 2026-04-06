from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    pass


class _Node:
    pass


class _TextNode(_Node):
    def __init__(self, text: str) -> None:
        self.text = text


class _VarNode(_Node):
    def __init__(self, name: str, filters: list[str]) -> None:
        self.name = name
        self.filters = filters


class _IfNode(_Node):
    def __init__(self, expr: str) -> None:
        self.expr = expr
        self.children: list[_Node] = []


class _ForNode(_Node):
    def __init__(self, loop_var: str, collection: str) -> None:
        self.loop_var = loop_var
        self.collection = collection
        self.children: list[_Node] = []


_PAT_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_PAT_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_PAT_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_PAT_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_PAT_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_PAT_SPLIT = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_PAT_CMP = re.compile(r"^(\w+)\s*(==|!=|>=?|<=?)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        self._filters[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        tokens = [t for t in _PAT_SPLIT.split(template) if t]
        tree = self._parse(tokens)
        return self._emit(tree, context)

    def _parse(self, tokens: list[str]) -> list[_Node]:
        root: list[_Node] = []
        stack: list[tuple[_Node, list[_Node]]] = []
        cur = root

        for tok in tokens:
            if m := _PAT_VAR.fullmatch(tok):
                segs = m.group(1).split("|")
                cur.append(_VarNode(segs[0], segs[1:]))
            elif m := _PAT_IF.fullmatch(tok):
                n = _IfNode(m.group(1))
                cur.append(n)
                stack.append((n, cur))
                cur = n.children
            elif _PAT_ENDIF.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, parent = stack.pop()
                if not isinstance(top, _IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                cur = parent
            elif m := _PAT_FOR.fullmatch(tok):
                n = _ForNode(m.group(1), m.group(2))
                cur.append(n)
                stack.append((n, cur))
                cur = n.children
            elif _PAT_ENDFOR.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, parent = stack.pop()
                if not isinstance(top, _ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                cur = parent
            elif tok:
                cur.append(_TextNode(tok))

        if stack:
            kind = "if" if isinstance(stack[-1][0], _IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")
        return root

    def _emit(self, nodes: list[_Node], ctx: dict[str, Any]) -> str:
        buf: list[str] = []
        for n in nodes:
            if isinstance(n, _TextNode):
                buf.append(n.text)
            elif isinstance(n, _VarNode):
                v = str(ctx.get(n.name, ""))
                for f in n.filters:
                    if f not in self._filters:
                        raise TemplateSyntaxError(f"Unknown filter: {f}")
                    v = self._filters[f](v)
                buf.append(v)
            elif isinstance(n, _IfNode):
                if self._truth(n.expr, ctx):
                    buf.append(self._emit(n.children, ctx))
            elif isinstance(n, _ForNode):
                seq = ctx.get(n.collection, [])
                for item in seq:
                    buf.append(self._emit(n.children, {**ctx, n.loop_var: item}))
        return "".join(buf)

    def _truth(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        if m := _PAT_CMP.match(expr):
            l = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            r = m.group(3).strip().strip("\"'")
            if op == "==":
                return l == r
            if op == "!=":
                return l != r
            try:
                lf, rf = float(l), float(r)
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
        return bool(ctx.get(expr, False))
