from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Raised for any malformed template syntax."""
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

_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_TOK = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_COMPARE = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


# ── Engine ───────────────────────────────────────────────────────────────

class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a named filter callable."""
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render a template string."""
        ast = self._parse(template)
        return self._render_ast(ast, context)

    # ── Parsing ───────────────────────────────────────────────────────

    def _parse(self, src: str) -> list[Node]:
        parts = _TOK.split(src)
        root: list[Node] = []
        frames: list[list[Node]] = [root]
        open_blocks: list[Node] = []

        for part in parts:
            if not part:
                continue

            m_v = _VAR.fullmatch(part)
            m_i = _IF.fullmatch(part)
            m_ei = _ENDIF.fullmatch(part)
            m_f = _FOR.fullmatch(part)
            m_ef = _ENDFOR.fullmatch(part)

            if m_v:
                segs = m_v.group(1).split("|")
                frames[-1].append(VarNode(segs[0], segs[1:]))
            elif m_i:
                n = IfNode(m_i.group(1))
                frames[-1].append(n)
                frames.append(n.children)
                open_blocks.append(n)
            elif m_ei:
                if not open_blocks or not isinstance(open_blocks[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                open_blocks.pop()
                frames.pop()
            elif m_f:
                n = ForNode(m_f.group(1), m_f.group(2))
                frames[-1].append(n)
                frames.append(n.children)
                open_blocks.append(n)
            elif m_ef:
                if not open_blocks or not isinstance(open_blocks[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                open_blocks.pop()
                frames.pop()
            else:
                frames[-1].append(TextNode(part))

        if open_blocks:
            tag = "if" if isinstance(open_blocks[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {tag} block")

        return root

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_ast(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        buf: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                buf.append(node.content)
            elif isinstance(node, VarNode):
                buf.append(self._var_value(node, ctx))
            elif isinstance(node, IfNode):
                if self._test_cond(node.condition, ctx):
                    buf.append(self._render_ast(node.children, ctx))
            elif isinstance(node, ForNode):
                seq = ctx.get(node.iterable, [])
                for item in seq:
                    buf.append(self._render_ast(node.children, {**ctx, node.var_name: item}))
        return "".join(buf)

    def _var_value(self, node: VarNode, ctx: dict[str, Any]) -> str:
        val = str(ctx.get(node.name, ""))
        for fn_name in node.filters:
            fn = self._filters.get(fn_name)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {fn_name}")
            val = fn(val)
        return val

    def _test_cond(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        m = _COMPARE.match(expr)
        if m:
            var, op, raw = m.group(1), m.group(2), m.group(3).strip().strip("\"'")
            lhs = str(ctx.get(var, ""))
            match op:
                case "==": return lhs == raw
                case "!=": return lhs != raw
                case ">":
                    try: return float(lhs) > float(raw)
                    except ValueError: return False
                case "<":
                    try: return float(lhs) < float(raw)
                    except ValueError: return False
                case ">=":
                    try: return float(lhs) >= float(raw)
                    except ValueError: return False
                case "<=":
                    try: return float(lhs) <= float(raw)
                    except ValueError: return False
        return bool(ctx.get(expr, False))
