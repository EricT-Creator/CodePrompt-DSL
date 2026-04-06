from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Raised for malformed templates: unclosed blocks, unknown filters, etc."""
    pass


# ── AST ──────────────────────────────────────────────────────────────────

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


# ── Regex ────────────────────────────────────────────────────────────────

_RX_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RX_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RX_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_RX_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RX_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_RX_TOKENIZE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RX_CMP = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


class TemplateEngine:
    """A regex-based template engine with variables, filters, conditionals, and loops."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a named filter for use in templates."""
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse *template* into an AST and render it with *context*."""
        ast = self._parse(template)
        return self._render_nodes(ast, context)

    # ── Parse ─────────────────────────────────────────────────────────

    def _parse(self, raw: str) -> list[Node]:
        fragments = _RX_TOKENIZE.split(raw)
        root: list[Node] = []
        frame: list[list[Node]] = [root]
        blocks: list[Node] = []

        for frag in fragments:
            if not frag:
                continue

            m_v = _RX_VAR.fullmatch(frag)
            m_if = _RX_IF.fullmatch(frag)
            m_ei = _RX_ENDIF.fullmatch(frag)
            m_for = _RX_FOR.fullmatch(frag)
            m_ef = _RX_ENDFOR.fullmatch(frag)

            if m_v:
                segs = m_v.group(1).split("|")
                frame[-1].append(VarNode(segs[0], segs[1:]))
            elif m_if:
                nd = IfNode(m_if.group(1))
                frame[-1].append(nd)
                frame.append(nd.children)
                blocks.append(nd)
            elif m_ei:
                if not blocks or not isinstance(blocks[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                blocks.pop()
                frame.pop()
            elif m_for:
                nd = ForNode(m_for.group(1), m_for.group(2))
                frame[-1].append(nd)
                frame.append(nd.children)
                blocks.append(nd)
            elif m_ef:
                if not blocks or not isinstance(blocks[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                blocks.pop()
                frame.pop()
            else:
                frame[-1].append(TextNode(frag))

        if blocks:
            tag = "if" if isinstance(blocks[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {tag} block")

        return root

    # ── Render ────────────────────────────────────────────────────────

    def _render_nodes(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        parts: list[str] = []
        for n in nodes:
            if isinstance(n, TextNode):
                parts.append(n.content)
            elif isinstance(n, VarNode):
                parts.append(self._eval_var(n, ctx))
            elif isinstance(n, IfNode):
                if self._eval_cond(n.condition, ctx):
                    parts.append(self._render_nodes(n.children, ctx))
            elif isinstance(n, ForNode):
                seq = ctx.get(n.iterable, [])
                for el in seq:
                    parts.append(self._render_nodes(n.children, {**ctx, n.var_name: el}))
        return "".join(parts)

    def _eval_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        s = str(ctx.get(node.name, ""))
        for f_name in node.filters:
            fn = self._filters.get(f_name)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {f_name}")
            s = fn(s)
        return s

    def _eval_cond(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        cm = _RX_CMP.match(expr)
        if cm:
            name, op, rhs = cm.group(1), cm.group(2), cm.group(3).strip().strip("\"'")
            lhs = str(ctx.get(name, ""))
            match op:
                case "==": return lhs == rhs
                case "!=": return lhs != rhs
                case ">":
                    try: return float(lhs) > float(rhs)
                    except ValueError: return False
                case "<":
                    try: return float(lhs) < float(rhs)
                    except ValueError: return False
                case ">=":
                    try: return float(lhs) >= float(rhs)
                    except ValueError: return False
                case "<=":
                    try: return float(lhs) <= float(rhs)
                    except ValueError: return False
        return bool(ctx.get(expr, False))
