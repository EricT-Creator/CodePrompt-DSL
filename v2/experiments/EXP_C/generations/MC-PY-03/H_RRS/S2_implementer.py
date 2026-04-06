"""Template Engine — MC-PY-03 (H × RRS)"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Union


# ─── Custom exception ───
class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line: int | None = line
        prefix = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")


# ─── AST Nodes ───
@dataclass
class TextNode:
    text: str


@dataclass
class VarNode:
    var_name: str
    filters: list[str]


@dataclass
class IfNode:
    condition: str
    true_branch: list[Node]
    false_branch: list[Node]


@dataclass
class ForNode:
    loop_var: str
    iterable_name: str
    body: list[Node]


Node = Union[TextNode, VarNode, IfNode, ForNode]


@dataclass
class RootNode:
    children: list[Node] = field(default_factory=list)


# ─── Regex patterns ───
TOKEN_PATTERN: re.Pattern[str] = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)
VAR_PATTERN: re.Pattern[str] = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
IF_OPEN: re.Pattern[str] = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ELSE_TAG: re.Pattern[str] = re.compile(r"\{%\s*else\s*%\}")
ENDIF_TAG: re.Pattern[str] = re.compile(r"\{%\s*endif\s*%\}")
FOR_OPEN: re.Pattern[str] = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_TAG: re.Pattern[str] = re.compile(r"\{%\s*endfor\s*%\}")


# ─── Filter Registry ───
class FilterRegistry:
    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
            "strip": str.strip,
            "title": str.title,
        }

    def register(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func

    def apply(self, value: str, filter_names: list[str]) -> str:
        result: str = value
        for name in filter_names:
            if name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {name}")
            result = self._filters[name](result)
        return result


# ─── Parser ───
class TemplateParser:
    def __init__(self) -> None:
        pass

    def parse(self, template: str) -> RootNode:
        tokens: list[str] = TOKEN_PATTERN.split(template)
        root = RootNode()
        stack: list[RootNode | IfNode | ForNode] = [root]
        in_else: set[int] = set()  # track which stack positions are in else branch

        for raw_token in tokens:
            if not raw_token:
                continue

            # Variable tag
            var_match = VAR_PATTERN.match(raw_token)
            if var_match:
                parts = var_match.group(1).split("|")
                var_name = parts[0]
                filters = parts[1:]
                node = VarNode(var_name=var_name, filters=filters)
                self._append_to_current(stack, node, in_else)
                continue

            # If open
            if_match = IF_OPEN.match(raw_token)
            if if_match:
                condition = if_match.group(1).strip()
                if_node = IfNode(condition=condition, true_branch=[], false_branch=[])
                self._append_to_current(stack, if_node, in_else)
                stack.append(if_node)
                continue

            # Else
            if ELSE_TAG.match(raw_token):
                if not stack or not isinstance(stack[-1], IfNode):
                    raise TemplateSyntaxError("else without matching if")
                in_else.add(id(stack[-1]))
                continue

            # Endif
            if ENDIF_TAG.match(raw_token):
                if not stack or not isinstance(stack[-1], IfNode):
                    raise TemplateSyntaxError("endif without matching if")
                in_else.discard(id(stack[-1]))
                stack.pop()
                continue

            # For open
            for_match = FOR_OPEN.match(raw_token)
            if for_match:
                loop_var = for_match.group(1)
                iterable_name = for_match.group(2)
                for_node = ForNode(loop_var=loop_var, iterable_name=iterable_name, body=[])
                self._append_to_current(stack, for_node, in_else)
                stack.append(for_node)
                continue

            # Endfor
            if ENDFOR_TAG.match(raw_token):
                if not stack or not isinstance(stack[-1], ForNode):
                    raise TemplateSyntaxError("endfor without matching for")
                stack.pop()
                continue

            # Check for malformed tags
            if raw_token.startswith("{%") or raw_token.startswith("{{"):
                raise TemplateSyntaxError(f"Invalid template tag: {raw_token.strip()}")

            # Plain text
            if raw_token:
                self._append_to_current(stack, TextNode(text=raw_token), in_else)

        # Validate stack
        if len(stack) > 1:
            top = stack[-1]
            if isinstance(top, IfNode):
                raise TemplateSyntaxError("Unclosed if block")
            elif isinstance(top, ForNode):
                raise TemplateSyntaxError("Unclosed for block")
            else:
                raise TemplateSyntaxError("Unclosed block")

        return root

    def _append_to_current(
        self,
        stack: list[RootNode | IfNode | ForNode],
        node: Node,
        in_else: set[int],
    ) -> None:
        current = stack[-1]
        if isinstance(current, RootNode):
            current.children.append(node)
        elif isinstance(current, IfNode):
            if id(current) in in_else:
                current.false_branch.append(node)
            else:
                current.true_branch.append(node)
        elif isinstance(current, ForNode):
            current.body.append(node)


# ─── Renderer ───
class TemplateRenderer:
    def __init__(self, filters: FilterRegistry, strict: bool = True) -> None:
        self._filters: FilterRegistry = filters
        self._strict: bool = strict

    def render(self, root: RootNode, context: dict[str, Any]) -> str:
        return self._render_nodes(root.children, context)

    def _render_nodes(self, nodes: list[Node], context: dict[str, Any]) -> str:
        parts: list[str] = []
        for node in nodes:
            parts.append(self._render_node(node, context))
        return "".join(parts)

    def _render_node(self, node: Node, context: dict[str, Any]) -> str:
        if isinstance(node, TextNode):
            return node.text

        if isinstance(node, VarNode):
            return self._render_var(node, context)

        if isinstance(node, IfNode):
            return self._render_if(node, context)

        if isinstance(node, ForNode):
            return self._render_for(node, context)

        return ""

    def _render_var(self, node: VarNode, context: dict[str, Any]) -> str:
        if node.var_name not in context:
            if self._strict:
                raise TemplateSyntaxError(f"Undefined variable: {node.var_name}")
            return ""
        value = str(context[node.var_name])
        if node.filters:
            value = self._filters.apply(value, node.filters)
        return value

    def _render_if(self, node: IfNode, context: dict[str, Any]) -> str:
        condition_val = self._evaluate_condition(node.condition, context)
        if condition_val:
            return self._render_nodes(node.true_branch, context)
        else:
            return self._render_nodes(node.false_branch, context)

    def _render_for(self, node: ForNode, context: dict[str, Any]) -> str:
        iterable = context.get(node.iterable_name)
        if iterable is None:
            if self._strict:
                raise TemplateSyntaxError(f"Undefined variable: {node.iterable_name}")
            return ""
        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(f"Variable '{node.iterable_name}' is not iterable")

        parts: list[str] = []
        for item in iterable:
            loop_ctx = {**context, node.loop_var: item}
            parts.append(self._render_nodes(node.body, loop_ctx))
        return "".join(parts)

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Simple condition evaluator — supports variable truthiness and basic comparisons."""
        condition = condition.strip()

        # Handle "not" prefix
        if condition.startswith("not "):
            return not self._evaluate_condition(condition[4:], context)

        # Handle equality / inequality
        for op in ("==", "!=", ">=", "<=", ">", "<"):
            if op in condition:
                left_str, right_str = condition.split(op, 1)
                left = self._resolve_value(left_str.strip(), context)
                right = self._resolve_value(right_str.strip(), context)
                if op == "==":
                    return left == right
                if op == "!=":
                    return left != right
                if op == ">=":
                    return left >= right  # type: ignore[operator]
                if op == "<=":
                    return left <= right  # type: ignore[operator]
                if op == ">":
                    return left > right  # type: ignore[operator]
                if op == "<":
                    return left < right  # type: ignore[operator]

        # Plain variable truthiness
        val = context.get(condition)
        return bool(val)

    def _resolve_value(self, token: str, context: dict[str, Any]) -> Any:
        """Resolve a token to a value — could be a variable name or a literal."""
        # String literal
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            return token[1:-1]
        # Integer literal
        try:
            return int(token)
        except ValueError:
            pass
        # Float literal
        try:
            return float(token)
        except ValueError:
            pass
        # Boolean
        if token == "True":
            return True
        if token == "False":
            return False
        if token == "None":
            return None
        # Variable
        return context.get(token)


# ─── Template Engine (public API) ───
class TemplateEngine:
    def __init__(self, strict: bool = True) -> None:
        self._parser: TemplateParser = TemplateParser()
        self._filters: FilterRegistry = FilterRegistry()
        self._renderer: TemplateRenderer = TemplateRenderer(self._filters, strict=strict)

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        ctx: dict[str, Any] = context or {}
        root = self._parser.parse(template)
        return self._renderer.render(root, ctx)

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters.register(name, func)


# ─── Main guard ───
if __name__ == "__main__":
    engine = TemplateEngine(strict=False)

    template = """Hello {{ name|upper }}!

{% if show_items %}Items:
{% for item in items %}- {{ item|capitalize }}
{% endfor %}{% endif %}
{% if not show_items %}No items to display.{% endif %}
"""

    context: dict[str, Any] = {
        "name": "world",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
    }

    output = engine.render(template, context)
    print(output)
