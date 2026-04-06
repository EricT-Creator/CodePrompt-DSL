from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    pass


class ASTNode:
    pass


class LiteralNode(ASTNode):
    def __init__(self, text: str) -> None:
        self.text = text


class VariableNode(ASTNode):
    def __init__(self, name: str, filters: list[str]) -> None:
        self.name = name
        self.filters = filters


class ConditionalNode(ASTNode):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.children: list[ASTNode] = []


class LoopNode(ASTNode):
    def __init__(self, var_name: str, iterable: str) -> None:
        self.var_name = var_name
        self.iterable = iterable
        self.children: list[ASTNode] = []


_RX_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RX_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RX_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_RX_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RX_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_RX_TOKENIZER = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RX_CMP = re.compile(r"^(\w+)\s*(==|!=|>=?|<=?)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._filter_map: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filter_map[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        raw = [p for p in _RX_TOKENIZER.split(template) if p]
        ast = self._build(raw)
        return self._output(ast, context)

    def _build(self, tokens: list[str]) -> list[ASTNode]:
        root: list[ASTNode] = []
        stack: list[tuple[ASTNode, list[ASTNode]]] = []
        target = root

        for tok in tokens:
            if m := _RX_VAR.fullmatch(tok):
                parts = m.group(1).split("|")
                target.append(VariableNode(parts[0], parts[1:]))
            elif m := _RX_IF.fullmatch(tok):
                nd = ConditionalNode(m.group(1))
                target.append(nd)
                stack.append((nd, target))
                target = nd.children
            elif _RX_ENDIF.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, prev = stack.pop()
                if not isinstance(top, ConditionalNode):
                    raise TemplateSyntaxError("Unexpected endif")
                target = prev
            elif m := _RX_FOR.fullmatch(tok):
                nd = LoopNode(m.group(1), m.group(2))
                target.append(nd)
                stack.append((nd, target))
                target = nd.children
            elif _RX_ENDFOR.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, prev = stack.pop()
                if not isinstance(top, LoopNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                target = prev
            elif tok:
                target.append(LiteralNode(tok))

        if stack:
            label = "if" if isinstance(stack[-1][0], ConditionalNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {label} block")
        return root

    def _output(self, nodes: list[ASTNode], ctx: dict[str, Any]) -> str:
        buf: list[str] = []
        for nd in nodes:
            if isinstance(nd, LiteralNode):
                buf.append(nd.text)
            elif isinstance(nd, VariableNode):
                val = str(ctx.get(nd.name, ""))
                for fname in nd.filters:
                    if fname not in self._filter_map:
                        raise TemplateSyntaxError(f"Unknown filter: {fname}")
                    val = self._filter_map[fname](val)
                buf.append(val)
            elif isinstance(nd, ConditionalNode):
                if self._check(nd.condition, ctx):
                    buf.append(self._output(nd.children, ctx))
            elif isinstance(nd, LoopNode):
                seq = ctx.get(nd.iterable, [])
                for item in seq:
                    buf.append(self._output(nd.children, {**ctx, nd.var_name: item}))
        return "".join(buf)

    def _check(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        if m := _RX_CMP.match(expr):
            left = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            right = m.group(3).strip().strip("\"'")
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            try:
                ln, rn = float(left), float(right)
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
