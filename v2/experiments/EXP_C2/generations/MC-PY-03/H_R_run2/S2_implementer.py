from __future__ import annotations

import re
from typing import Any, Callable


class TemplateSyntaxError(Exception):
    """Raised when a template contains malformed syntax."""
    pass


# ─── AST Nodes ────────────────────────────────────────────────────────────

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


# ─── Regex Patterns ───────────────────────────────────────────────────────

_VAR_RE = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
_IF_OPEN_RE = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
_IF_CLOSE_RE = re.compile(r"\{%\s*endif\s*%\}")
_FOR_OPEN_RE = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
_FOR_CLOSE_RE = re.compile(r"\{%\s*endfor\s*%\}")
_TOKENIZER_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")

_CMP_RE = re.compile(r"^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


# ─── Template Engine ─────────────────────────────────────────────────────

class TemplateEngine:

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Register a custom filter function."""
        self._filters[name] = func

    # ── Public API ────────────────────────────────────────────────────

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Parse and render *template* using *context*."""
        ast = self._parse(template)
        return self._render_nodes(ast, context)

    # ── Parsing ───────────────────────────────────────────────────────

    def _parse(self, template: str) -> list[Node]:
        tokens = _TOKENIZER_RE.split(template)
        root: list[Node] = []
        stack: list[list[Node]] = [root]
        block_stack: list[Node] = []

        for token in tokens:
            if not token:
                continue

            m_var = _VAR_RE.fullmatch(token)
            m_if = _IF_OPEN_RE.fullmatch(token)
            m_endif = _IF_CLOSE_RE.fullmatch(token)
            m_for = _FOR_OPEN_RE.fullmatch(token)
            m_endfor = _FOR_CLOSE_RE.fullmatch(token)

            if m_var:
                parts = m_var.group(1).split("|")
                name = parts[0]
                filters = parts[1:]
                stack[-1].append(VarNode(name, filters))
            elif m_if:
                node = IfNode(m_if.group(1))
                stack[-1].append(node)
                stack.append(node.children)
                block_stack.append(node)
            elif m_endif:
                if not block_stack or not isinstance(block_stack[-1], IfNode):
                    raise TemplateSyntaxError("Unexpected endif")
                block_stack.pop()
                stack.pop()
            elif m_for:
                node = ForNode(m_for.group(1), m_for.group(2))
                stack[-1].append(node)
                stack.append(node.children)
                block_stack.append(node)
            elif m_endfor:
                if not block_stack or not isinstance(block_stack[-1], ForNode):
                    raise TemplateSyntaxError("Unexpected endfor")
                block_stack.pop()
                stack.pop()
            else:
                stack[-1].append(TextNode(token))

        if block_stack:
            node = block_stack[-1]
            kind = "if" if isinstance(node, IfNode) else "for"
            raise TemplateSyntaxError(f"Unclosed {kind} block")

        return root

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_nodes(self, nodes: list[Node], context: dict[str, Any]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, TextNode):
                parts.append(node.content)
            elif isinstance(node, VarNode):
                parts.append(self._render_var(node, context))
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, context):
                    parts.append(self._render_nodes(node.children, context))
            elif isinstance(node, ForNode):
                iterable = context.get(node.iterable_name, [])
                for item in iterable:
                    child_ctx = {**context, node.var_name: item}
                    parts.append(self._render_nodes(node.children, child_ctx))
        return "".join(parts)

    def _render_var(self, node: VarNode, context: dict[str, Any]) -> str:
        value = context.get(node.name, "")
        result = str(value)
        for f_name in node.filters:
            func = self._filters.get(f_name)
            if func is None:
                raise TemplateSyntaxError(f"Unknown filter: {f_name}")
            result = func(result)
        return result

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        condition = condition.strip()
        m = _CMP_RE.match(condition)
        if m:
            var_name, op, raw_value = m.group(1), m.group(2), m.group(3).strip().strip("\"'")
            left = str(context.get(var_name, ""))
            match op:
                case "==":
                    return left == raw_value
                case "!=":
                    return left != raw_value
                case ">":
                    try:
                        return float(left) > float(raw_value)
                    except ValueError:
                        return False
                case "<":
                    try:
                        return float(left) < float(raw_value)
                    except ValueError:
                        return False
                case ">=":
                    try:
                        return float(left) >= float(raw_value)
                    except ValueError:
                        return False
                case "<=":
                    try:
                        return float(left) <= float(raw_value)
                    except ValueError:
                        return False
        return bool(context.get(condition, False))
