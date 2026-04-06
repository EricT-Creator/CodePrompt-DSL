from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    pass


class BaseNode:
    pass


class TextChunk(BaseNode):
    def __init__(self, content: str) -> None:
        self.content = content


class VarRef(BaseNode):
    def __init__(self, name: str, filters: list[str]) -> None:
        self.name = name
        self.filters = filters


class IfBlock(BaseNode):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.children: list[BaseNode] = []


class ForBlock(BaseNode):
    def __init__(self, var_name: str, iterable: str) -> None:
        self.var_name = var_name
        self.iterable = iterable
        self.children: list[BaseNode] = []


_R_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_R_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_R_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_R_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_R_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_R_SPLIT = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_R_CMP = re.compile(r"^(\w+)\s*(==|!=|>=?|<=?)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._builtins: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        self._builtins[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        chunks = [c for c in _R_SPLIT.split(template) if c]
        tree = self._parse(chunks)
        return self._walk(tree, context)

    def _parse(self, tokens: list[str]) -> list[BaseNode]:
        root: list[BaseNode] = []
        stack: list[tuple[BaseNode, list[BaseNode]]] = []
        dest = root

        for tok in tokens:
            if m := _R_VAR.fullmatch(tok):
                ps = m.group(1).split("|")
                dest.append(VarRef(ps[0], ps[1:]))
            elif m := _R_IF.fullmatch(tok):
                blk = IfBlock(m.group(1))
                dest.append(blk)
                stack.append((blk, dest))
                dest = blk.children
            elif _R_ENDIF.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, prev = stack.pop()
                if not isinstance(top, IfBlock):
                    raise TemplateSyntaxError("Unexpected endif")
                dest = prev
            elif m := _R_FOR.fullmatch(tok):
                blk = ForBlock(m.group(1), m.group(2))
                dest.append(blk)
                stack.append((blk, dest))
                dest = blk.children
            elif _R_ENDFOR.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, prev = stack.pop()
                if not isinstance(top, ForBlock):
                    raise TemplateSyntaxError("Unexpected endfor")
                dest = prev
            elif tok:
                dest.append(TextChunk(tok))

        if stack:
            tag = "if" if isinstance(stack[-1][0], IfBlock) else "for"
            raise TemplateSyntaxError(f"Unclosed {tag} block")
        return root

    def _walk(self, nodes: list[BaseNode], ctx: dict[str, Any]) -> str:
        acc: list[str] = []
        for nd in nodes:
            if isinstance(nd, TextChunk):
                acc.append(nd.content)
            elif isinstance(nd, VarRef):
                s = str(ctx.get(nd.name, ""))
                for f in nd.filters:
                    if f not in self._builtins:
                        raise TemplateSyntaxError(f"Unknown filter: {f}")
                    s = self._builtins[f](s)
                acc.append(s)
            elif isinstance(nd, IfBlock):
                if self._eval(nd.condition, ctx):
                    acc.append(self._walk(nd.children, ctx))
            elif isinstance(nd, ForBlock):
                lst = ctx.get(nd.iterable, [])
                for el in lst:
                    acc.append(self._walk(nd.children, {**ctx, nd.var_name: el}))
        return "".join(acc)

    def _eval(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        if m := _R_CMP.match(expr):
            lhs = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            rhs = m.group(3).strip().strip("\"'")
            if op == "==":
                return lhs == rhs
            if op == "!=":
                return lhs != rhs
            try:
                ln, rn = float(lhs), float(rhs)
            except ValueError:
                return False
            if op == ">":
                return ln > rn
            if op == "<":
                return ln < rn
            if op == ">=":
                return ln >= rn
            if op == "<=":
                return ln <= rn
        return bool(ctx.get(expr, False))
