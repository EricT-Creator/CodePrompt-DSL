from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Custom exception for malformed template input."""
    pass


# ── Node Types ───────────────────────────────────────────────────────────

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


# ── Compiled Patterns ────────────────────────────────────────────────────

_P_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_P_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_P_ENDIF = re.compile(r"\{%\s*endif\s*%\}")
_P_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_P_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}")
_P_SPLIT = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_P_CMP = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


# ── TemplateEngine ───────────────────────────────────────────────────────

class TemplateEngine:

    def __init__(self) -> None:
        self._filter_registry: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter by name."""
        self._filter_registry[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render *template* against *context*."""
        nodes = self._parse(template)
        return self._render_nodes(nodes, context)

    # ── Parsing ───────────────────────────────────────────────────────

    def _parse(self, template: str) -> list[Node]:
        segments = _P_SPLIT.split(template)
        root: list[Node] = []
        stack: list[list[Node]] = [root]
        blocks: list[Node] = []

        for seg in segments:
            if not seg:
                continue

            var_m = _P_VAR.fullmatch(seg)
            if_m = _P_IF.fullmatch(seg)
            endif_m = _P_ENDIF.fullmatch(seg)
            for_m = _P_FOR.fullmatch(seg)
            endfor_m = _P_ENDFOR.fullmatch(seg)

            if var_m:
                pieces = var_m.group(1).split("|")
                stack[-1].append(VarNode(pieces[0], pieces[1:]))
            elif if_m:
                n = IfNode(if_m.group(1))
                stack[-1].append(n)
                stack.append(n.body)
                blocks.append(n)
            elif endif_m:
                if not blocks or not isinstance(blocks[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                blocks.pop()
                stack.pop()
            elif for_m:
                n = ForNode(for_m.group(1), for_m.group(2))
                stack[-1].append(n)
                stack.append(n.body)
                blocks.append(n)
            elif endfor_m:
                if not blocks or not isinstance(blocks[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                blocks.pop()
                stack.pop()
            else:
                stack[-1].append(TextNode(seg))

        if blocks:
            label = "if" if isinstance(blocks[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {label} block")

        return root

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_nodes(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        output: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                output.append(node.content)
            elif isinstance(node, VarNode):
                output.append(self._apply_var(node, ctx))
            elif isinstance(node, IfNode):
                if self._eval_condition(node.condition, ctx):
                    output.append(self._render_nodes(node.body, ctx))
            elif isinstance(node, ForNode):
                collection = ctx.get(node.iterable, [])
                for elem in collection:
                    inner_ctx = {**ctx, node.loop_var: elem}
                    output.append(self._render_nodes(node.body, inner_ctx))
        return "".join(output)

    def _apply_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        raw = ctx.get(node.name, "")
        result = str(raw)
        for fname in node.filters:
            fn = self._filter_registry.get(fname)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {fname}")
            result = fn(result)
        return result

    def _eval_condition(self, cond: str, ctx: dict[str, Any]) -> bool:
        cond = cond.strip()
        cm = _P_CMP.match(cond)
        if cm:
            lhs_name, operator, rhs_raw = cm.group(1), cm.group(2), cm.group(3).strip().strip("\"'")
            lhs = str(ctx.get(lhs_name, ""))
            match operator:
                case "==": return lhs == rhs_raw
                case "!=": return lhs != rhs_raw
                case ">":
                    try: return float(lhs) > float(rhs_raw)
                    except ValueError: return False
                case "<":
                    try: return float(lhs) < float(rhs_raw)
                    except ValueError: return False
                case ">=":
                    try: return float(lhs) >= float(rhs_raw)
                    except ValueError: return False
                case "<=":
                    try: return float(lhs) <= float(rhs_raw)
                    except ValueError: return False
        return bool(ctx.get(cond, False))
