from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Raised on malformed template input."""
    pass


# ── AST Node Types ───────────────────────────────────────────────────────

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


# ── Patterns ─────────────────────────────────────────────────────────────

_RE_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RE_IF_OPEN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RE_IF_CLOSE = re.compile(r"\{%\s*endif\s*%\}")
_RE_FOR_OPEN = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RE_FOR_CLOSE = re.compile(r"\{%\s*endfor\s*%\}")
_RE_TOKEN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RE_CMP = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


# ── Engine ───────────────────────────────────────────────────────────────

class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, fn: Callable[[str], str]) -> None:
        """Add a named filter to the engine."""
        self._filters[name] = fn

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse *template* and produce output using *context*."""
        tree = self._build_tree(template)
        return self._eval_nodes(tree, context)

    # ── Parse ─────────────────────────────────────────────────────────

    def _build_tree(self, template: str) -> list[Node]:
        tokens = _RE_TOKEN.split(template)
        root: list[Node] = []
        frame_stack: list[list[Node]] = [root]
        block_stack: list[Node] = []

        for tok in tokens:
            if not tok:
                continue

            mv = _RE_VAR.fullmatch(tok)
            mi = _RE_IF_OPEN.fullmatch(tok)
            mei = _RE_IF_CLOSE.fullmatch(tok)
            mf = _RE_FOR_OPEN.fullmatch(tok)
            mef = _RE_FOR_CLOSE.fullmatch(tok)

            if mv:
                parts = mv.group(1).split("|")
                frame_stack[-1].append(VarNode(parts[0], parts[1:]))
            elif mi:
                node = IfNode(mi.group(1))
                frame_stack[-1].append(node)
                frame_stack.append(node.children)
                block_stack.append(node)
            elif mei:
                if not block_stack or not isinstance(block_stack[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                block_stack.pop()
                frame_stack.pop()
            elif mf:
                node = ForNode(mf.group(1), mf.group(2))
                frame_stack[-1].append(node)
                frame_stack.append(node.children)
                block_stack.append(node)
            elif mef:
                if not block_stack or not isinstance(block_stack[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                block_stack.pop()
                frame_stack.pop()
            else:
                frame_stack[-1].append(TextNode(tok))

        if block_stack:
            kind = "if" if isinstance(block_stack[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")

        return root

    # ── Render ────────────────────────────────────────────────────────

    def _eval_nodes(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        out: list[str] = []
        for n in nodes:
            if isinstance(n, TextNode):
                out.append(n.content)
            elif isinstance(n, VarNode):
                out.append(self._resolve_var(n, ctx))
            elif isinstance(n, IfNode):
                if self._check_cond(n.condition, ctx):
                    out.append(self._eval_nodes(n.children, ctx))
            elif isinstance(n, ForNode):
                items = ctx.get(n.iterable_name, [])
                for item in items:
                    child = {**ctx, n.var_name: item}
                    out.append(self._eval_nodes(n.children, child))
        return "".join(out)

    def _resolve_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        val = str(ctx.get(node.name, ""))
        for fname in node.filters:
            fn = self._filters.get(fname)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {fname}")
            val = fn(val)
        return val

    def _check_cond(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        m = _RE_CMP.match(cond)
        if m:
            var, op, rhs = m.group(1), m.group(2), m.group(3).strip().strip("\"'")
            lhs = str(ctx.get(var, ""))
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
        return bool(ctx.get(cond, False))
