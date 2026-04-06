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
        self.body: list[Node] = []


class ForNode(Node):
    def __init__(self, loop_var: str, iterable: str) -> None:
        self.loop_var = loop_var
        self.iterable = iterable
        self.body: list[Node] = []


_VAR_PAT = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF_PAT = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_ENDIF_PAT = re.compile(r"\{%\s*endif\s*%\}")
_FOR_PAT = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_ENDFOR_PAT = re.compile(r"\{%\s*endfor\s*%\}")
_SPLITTER = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_CMP_PAT = re.compile(r"^(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)$")


class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        tokens = [t for t in _SPLITTER.split(template) if t]
        tree = self._parse(tokens)
        return self._evaluate(tree, context)

    def _parse(self, tokens: list[str]) -> list[Node]:
        root: list[Node] = []
        stack: list[tuple[Node, list[Node]]] = []
        current = root

        for tok in tokens:
            if m := _VAR_PAT.fullmatch(tok):
                parts = m.group(1).split("|")
                current.append(VarNode(parts[0], parts[1:]))
            elif m := _IF_PAT.fullmatch(tok):
                node = IfNode(m.group(1))
                current.append(node)
                stack.append((node, current))
                current = node.body
            elif _ENDIF_PAT.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, parent = stack.pop()
                if not isinstance(top, IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                current = parent
            elif m := _FOR_PAT.fullmatch(tok):
                node = ForNode(m.group(1), m.group(2))
                current.append(node)
                stack.append((node, current))
                current = node.body
            elif _ENDFOR_PAT.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, parent = stack.pop()
                if not isinstance(top, ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                current = parent
            else:
                if tok:
                    current.append(TextNode(tok))

        if stack:
            kind = "if" if isinstance(stack[-1][0], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")
        return root

    def _evaluate(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                parts.append(node.content)
            elif isinstance(node, VarNode):
                val = str(ctx.get(node.name, ""))
                for f in node.filters:
                    if f not in self._filters:
                        raise TemplateSyntaxError(f"Unknown filter: {f}")
                    val = self._filters[f](val)
                parts.append(val)
            elif isinstance(node, IfNode):
                if self._eval_cond(node.condition, ctx):
                    parts.append(self._evaluate(node.body, ctx))
            elif isinstance(node, ForNode):
                items = ctx.get(node.iterable, [])
                for item in items:
                    parts.append(self._evaluate(node.body, {**ctx, node.loop_var: item}))
        return "".join(parts)

    def _eval_cond(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        if m := _CMP_PAT.match(cond):
            lhs = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            rhs = m.group(3).strip().strip("\"'")
            if op == "==":
                return lhs == rhs
            if op == "!=":
                return lhs != rhs
            try:
                lf, rf = float(lhs), float(rhs)
            except ValueError:
                lf, rf = lhs, rhs  # type: ignore[assignment]
            if op == ">":
                return lf > rf
            if op == "<":
                return lf < rf
            if op == ">=":
                return lf >= rf
            if op == "<=":
                return lf <= rf
        return bool(ctx.get(cond, False))
