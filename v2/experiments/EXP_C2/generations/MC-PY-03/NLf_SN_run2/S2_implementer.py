from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Exception for malformed template input."""
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
    def __init__(self, var_name: str, iterable: str) -> None:
        self.var_name = var_name
        self.iterable = iterable
        self.children: list[Node] = []


# ── Compiled Patterns ────────────────────────────────────────────────────

_P_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_P_IF_OPEN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_P_IF_CLOSE = re.compile(r"\{%\s*endif\s*%\}")
_P_FOR_OPEN = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_P_FOR_CLOSE = re.compile(r"\{%\s*endfor\s*%\}")
_P_TOKENIZER = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_P_CMP = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


class TemplateEngine:
    """A single-class template engine built on regex parsing."""

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Add a named filter to the registry."""
        self._registry[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse *template*, apply *context*, and return the rendered string."""
        tree = self._build_ast(template)
        return self._emit(tree, context)

    # ── AST Construction ──────────────────────────────────────────────

    def _build_ast(self, src: str) -> list[Node]:
        tokens = _P_TOKENIZER.split(src)
        root: list[Node] = []
        stack: list[list[Node]] = [root]
        pending: list[Node] = []

        for tok in tokens:
            if not tok:
                continue

            v = _P_VAR.fullmatch(tok)
            io = _P_IF_OPEN.fullmatch(tok)
            ic = _P_IF_CLOSE.fullmatch(tok)
            fo = _P_FOR_OPEN.fullmatch(tok)
            fc = _P_FOR_CLOSE.fullmatch(tok)

            if v:
                parts = v.group(1).split("|")
                stack[-1].append(VarNode(parts[0], parts[1:]))
            elif io:
                node = IfNode(io.group(1))
                stack[-1].append(node)
                stack.append(node.children)
                pending.append(node)
            elif ic:
                if not pending or not isinstance(pending[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                pending.pop()
                stack.pop()
            elif fo:
                node = ForNode(fo.group(1), fo.group(2))
                stack[-1].append(node)
                stack.append(node.children)
                pending.append(node)
            elif fc:
                if not pending or not isinstance(pending[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                pending.pop()
                stack.pop()
            else:
                stack[-1].append(TextNode(tok))

        if pending:
            kind = "if" if isinstance(pending[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")

        return root

    # ── Rendering ─────────────────────────────────────────────────────

    def _emit(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        buf: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                buf.append(node.content)
            elif isinstance(node, VarNode):
                buf.append(self._resolve(node, ctx))
            elif isinstance(node, IfNode):
                if self._truthful(node.condition, ctx):
                    buf.append(self._emit(node.children, ctx))
            elif isinstance(node, ForNode):
                seq = ctx.get(node.iterable, [])
                for elem in seq:
                    buf.append(self._emit(node.children, {**ctx, node.var_name: elem}))
        return "".join(buf)

    def _resolve(self, node: VarNode, ctx: dict[str, Any]) -> str:
        val = str(ctx.get(node.name, ""))
        for fname in node.filters:
            fn = self._registry.get(fname)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {fname}")
            val = fn(val)
        return val

    def _truthful(self, expr: str, ctx: dict[str, Any]) -> bool:
        expr = expr.strip()
        m = _P_CMP.match(expr)
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
        return bool(ctx.get(expr, False))
