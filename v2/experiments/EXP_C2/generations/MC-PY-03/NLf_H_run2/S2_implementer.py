from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Exception for malformed template constructs."""
    pass


# ── Node Hierarchy ───────────────────────────────────────────────────────

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
    def __init__(self, loop_var: str, collection: str) -> None:
        self.loop_var = loop_var
        self.collection = collection
        self.children: list[Node] = []


# ── Patterns ─────────────────────────────────────────────────────────────

_VAR_PAT = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF_PAT = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_ENDIF_PAT = re.compile(r"\{%\s*endif\s*%\}")
_FOR_PAT = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_ENDFOR_PAT = re.compile(r"\{%\s*endfor\s*%\}")
_SPLIT_PAT = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_CMP_PAT = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


class TemplateEngine:
    """Regex-based template engine with variable substitution, filters, conditionals, and loops."""

    def __init__(self) -> None:
        self._filter_map: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        """Add a filter function to the engine."""
        self._filter_map[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Compile and render *template* using *context*."""
        nodes = self._compile(template)
        return self._output(nodes, context)

    # ── Compilation ───────────────────────────────────────────────────

    def _compile(self, src: str) -> list[Node]:
        pieces = _SPLIT_PAT.split(src)
        root: list[Node] = []
        stack: list[list[Node]] = [root]
        opens: list[Node] = []

        for piece in pieces:
            if not piece:
                continue

            mv = _VAR_PAT.fullmatch(piece)
            mi = _IF_PAT.fullmatch(piece)
            mei = _ENDIF_PAT.fullmatch(piece)
            mf = _FOR_PAT.fullmatch(piece)
            mef = _ENDFOR_PAT.fullmatch(piece)

            if mv:
                parts = mv.group(1).split("|")
                stack[-1].append(VarNode(parts[0], parts[1:]))
            elif mi:
                n = IfNode(mi.group(1))
                stack[-1].append(n)
                stack.append(n.children)
                opens.append(n)
            elif mei:
                if not opens or not isinstance(opens[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                opens.pop()
                stack.pop()
            elif mf:
                n = ForNode(mf.group(1), mf.group(2))
                stack[-1].append(n)
                stack.append(n.children)
                opens.append(n)
            elif mef:
                if not opens or not isinstance(opens[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                opens.pop()
                stack.pop()
            else:
                stack[-1].append(TextNode(piece))

        if opens:
            tag = "if" if isinstance(opens[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {tag} block")

        return root

    # ── Output ────────────────────────────────────────────────────────

    def _output(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        segments: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                segments.append(node.content)
            elif isinstance(node, VarNode):
                segments.append(self._format_var(node, ctx))
            elif isinstance(node, IfNode):
                if self._is_truthy(node.condition, ctx):
                    segments.append(self._output(node.children, ctx))
            elif isinstance(node, ForNode):
                items = ctx.get(node.collection, [])
                for item in items:
                    segments.append(self._output(node.children, {**ctx, node.loop_var: item}))
        return "".join(segments)

    def _format_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        raw = str(ctx.get(node.name, ""))
        for f in node.filters:
            func = self._filter_map.get(f)
            if func is None:
                raise TemplateSyntaxError(f"Unknown filter: {f}")
            raw = func(raw)
        return raw

    def _is_truthy(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        cm = _CMP_PAT.match(expr)
        if cm:
            key, op, val = cm.group(1), cm.group(2), cm.group(3).strip().strip("\"'")
            left = str(ctx.get(key, ""))
            match op:
                case "==": return left == val
                case "!=": return left != val
                case ">":
                    try: return float(left) > float(val)
                    except ValueError: return False
                case "<":
                    try: return float(left) < float(val)
                    except ValueError: return False
                case ">=":
                    try: return float(left) >= float(val)
                    except ValueError: return False
                case "<=":
                    try: return float(left) <= float(val)
                    except ValueError: return False
        return bool(ctx.get(expr, False))
