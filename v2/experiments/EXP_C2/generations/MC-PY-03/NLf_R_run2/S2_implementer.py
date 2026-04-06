from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Custom exception for template syntax errors."""
    pass


# ── AST Nodes ────────────────────────────────────────────────────────────

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


# ── Compiled Regex ───────────────────────────────────────────────────────

_RE_VAR = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_RE_IF_START = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_RE_IF_END = re.compile(r"\{%\s*endif\s*%\}")
_RE_FOR_START = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_RE_FOR_END = re.compile(r"\{%\s*endfor\s*%\}")
_RE_MASTER = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")
_RE_COMPARISON = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


class TemplateEngine:
    """A regex-based template engine supporting variables, filters, conditionals, and loops."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter function."""
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render *template* with the given *context* dictionary."""
        tree = self._parse(template)
        return self._render_tree(tree, context)

    # ── Parsing ───────────────────────────────────────────────────────

    def _parse(self, template: str) -> list[Node]:
        tokens = _RE_MASTER.split(template)
        root: list[Node] = []
        node_stack: list[list[Node]] = [root]
        block_stack: list[Node] = []

        for token in tokens:
            if not token:
                continue

            var_match = _RE_VAR.fullmatch(token)
            if_match = _RE_IF_START.fullmatch(token)
            endif_match = _RE_IF_END.fullmatch(token)
            for_match = _RE_FOR_START.fullmatch(token)
            endfor_match = _RE_FOR_END.fullmatch(token)

            if var_match:
                segments = var_match.group(1).split("|")
                node_stack[-1].append(VarNode(segments[0], segments[1:]))
            elif if_match:
                node = IfNode(if_match.group(1))
                node_stack[-1].append(node)
                node_stack.append(node.children)
                block_stack.append(node)
            elif endif_match:
                if not block_stack or not isinstance(block_stack[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                block_stack.pop()
                node_stack.pop()
            elif for_match:
                node = ForNode(for_match.group(1), for_match.group(2))
                node_stack[-1].append(node)
                node_stack.append(node.children)
                block_stack.append(node)
            elif endfor_match:
                if not block_stack or not isinstance(block_stack[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                block_stack.pop()
                node_stack.pop()
            else:
                node_stack[-1].append(TextNode(token))

        if block_stack:
            kind = "if" if isinstance(block_stack[-1], IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")

        return root

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_tree(self, nodes: list[Node], ctx: dict[str, Any]) -> str:
        result: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                result.append(node.content)
            elif isinstance(node, VarNode):
                result.append(self._resolve_var(node, ctx))
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, ctx):
                    result.append(self._render_tree(node.children, ctx))
            elif isinstance(node, ForNode):
                items = ctx.get(node.iterable_name, [])
                for item in items:
                    loop_ctx = {**ctx, node.var_name: item}
                    result.append(self._render_tree(node.children, loop_ctx))
        return "".join(result)

    def _resolve_var(self, node: VarNode, ctx: dict[str, Any]) -> str:
        value = str(ctx.get(node.name, ""))
        for filter_name in node.filters:
            fn = self._filters.get(filter_name)
            if fn is None:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            value = fn(value)
        return value

    def _evaluate_condition(self, expression: str, ctx: dict[str, Any]) -> bool:
        expression = expression.strip()
        cmp_match = _RE_COMPARISON.match(expression)
        if cmp_match:
            var_name = cmp_match.group(1)
            operator = cmp_match.group(2)
            right_val = cmp_match.group(3).strip().strip("\"'")
            left_val = str(ctx.get(var_name, ""))
            match operator:
                case "==":
                    return left_val == right_val
                case "!=":
                    return left_val != right_val
                case ">":
                    try:
                        return float(left_val) > float(right_val)
                    except ValueError:
                        return False
                case "<":
                    try:
                        return float(left_val) < float(right_val)
                    except ValueError:
                        return False
                case ">=":
                    try:
                        return float(left_val) >= float(right_val)
                    except ValueError:
                        return False
                case "<=":
                    try:
                        return float(left_val) <= float(right_val)
                    except ValueError:
                        return False
        return bool(ctx.get(expression, False))
