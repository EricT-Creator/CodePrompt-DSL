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


_RE_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RE_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RE_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_RE_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RE_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_RE_TOKENIZE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RE_CMP = re.compile(r"^(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)$")


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
        tokens = self._tokenize(template)
        tree = self._build_tree(tokens)
        return self._eval_nodes(tree, context)

    def _tokenize(self, template: str) -> list[str]:
        return [p for p in _RE_TOKENIZE.split(template) if p]

    def _build_tree(self, tokens: list[str]) -> list[Node]:
        root: list[Node] = []
        stack: list[tuple[Node, list[Node]]] = []
        current = root

        for tok in tokens:
            if m := _RE_VAR.fullmatch(tok):
                parts = m.group(1).split("|")
                current.append(VarNode(parts[0], parts[1:]))
            elif m := _RE_IF.fullmatch(tok):
                node = IfNode(m.group(1))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif _RE_ENDIF.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endif")
                top, parent = stack.pop()
                if not isinstance(top, IfNode):
                    raise TemplateSyntaxError("Unexpected endif — expected endfor")
                current = parent
            elif m := _RE_FOR.fullmatch(tok):
                node = ForNode(m.group(1), m.group(2))
                current.append(node)
                stack.append((node, current))
                current = node.children
            elif _RE_ENDFOR.fullmatch(tok):
                if not stack:
                    raise TemplateSyntaxError("Unexpected endfor")
                top, parent = stack.pop()
                if not isinstance(top, ForNode):
                    raise TemplateSyntaxError("Unexpected endfor — expected endif")
                current = parent
            else:
                if tok:
                    current.append(TextNode(tok))

        if stack:
            kind = "if" if isinstance(stack[-1][0], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")
        return root

    def _eval_nodes(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        out: list[str] = []
        for n in nodes:
            if isinstance(n, TextNode):
                out.append(n.content)
            elif isinstance(n, VarNode):
                out.append(self._eval_var(n, ctx))
            elif isinstance(n, IfNode):
                if self._check_cond(n.condition, ctx):
                    out.append(self._eval_nodes(n.children, ctx))
            elif isinstance(n, ForNode):
                seq = ctx.get(n.iterable_name, [])
                for item in seq:
                    out.append(self._eval_nodes(n.children, {**ctx, n.var_name: item}))
        return "".join(out)

    def _eval_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        val = str(ctx.get(node.name, ""))
        for fname in node.filters:
            if fname not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {fname}")
            val = self._filters[fname](val)
        return val

    def _check_cond(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        if m := _RE_CMP.match(cond):
            lhs = str(ctx.get(m.group(1), ""))
            op = m.group(2)
            rhs = m.group(3).strip().strip("\"'")
            match op:
                case "==": return lhs == rhs
                case "!=": return lhs != rhs
                case ">":
                    try: return float(lhs) > float(rhs)
                    except ValueError: return lhs > rhs
                case "<":
                    try: return float(lhs) < float(rhs)
                    except ValueError: return lhs < rhs
                case ">=":
                    try: return float(lhs) >= float(rhs)
                    except ValueError: return lhs >= rhs
                case "<=":
                    try: return float(lhs) <= float(rhs)
                    except ValueError: return lhs <= rhs
        return bool(ctx.get(cond, False))
