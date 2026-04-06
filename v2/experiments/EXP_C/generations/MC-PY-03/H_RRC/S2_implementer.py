"""Template Engine — MC-PY-03 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Custom Exception ───


class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line: int | None = line
        prefix: str = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")


# ─── AST Node Types ───


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


Node = TextNode | VarNode | IfNode | ForNode


# ─── Regex Patterns ───

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

    def parse(self, template: str) -> list[Node]:
        tokens: list[str] = TOKEN_PATTERN.split(template)
        nodes: list[Node] = []
        stack: list[IfNode | ForNode] = []

        def current_children() -> list[Node]:
            if not stack:
                return nodes
            top = stack[-1]
            if isinstance(top, IfNode):
                if hasattr(top, "_in_else") and top._in_else:  # type: ignore[attr-defined]
                    return top.false_branch
                return top.true_branch
            if isinstance(top, ForNode):
                return top.body
            return nodes

        for token in tokens:
            if not token:
                continue

            # Variable tag
            var_match: re.Match[str] | None = VAR_PATTERN.match(token)
            if var_match:
                raw: str = var_match.group(1)
                parts: list[str] = raw.split("|")
                var_name: str = parts[0]
                filters: list[str] = parts[1:] if len(parts) > 1 else []
                current_children().append(VarNode(var_name=var_name, filters=filters))
                continue

            # If open tag
            if_match: re.Match[str] | None = IF_OPEN.match(token)
            if if_match:
                condition: str = if_match.group(1).strip()
                node: IfNode = IfNode(
                    condition=condition, true_branch=[], false_branch=[]
                )
                node._in_else = False  # type: ignore[attr-defined]
                current_children().append(node)
                stack.append(node)
                continue

            # Else tag
            if ELSE_TAG.match(token):
                if not stack or not isinstance(stack[-1], IfNode):
                    raise TemplateSyntaxError("else without matching if")
                stack[-1]._in_else = True  # type: ignore[attr-defined]
                continue

            # Endif tag
            if ENDIF_TAG.match(token):
                if not stack or not isinstance(stack[-1], IfNode):
                    raise TemplateSyntaxError("endif without matching if")
                stack.pop()
                continue

            # For open tag
            for_match: re.Match[str] | None = FOR_OPEN.match(token)
            if for_match:
                loop_var: str = for_match.group(1)
                iterable_name: str = for_match.group(2)
                for_node: ForNode = ForNode(
                    loop_var=loop_var, iterable_name=iterable_name, body=[]
                )
                current_children().append(for_node)
                stack.append(for_node)
                continue

            # Endfor tag
            if ENDFOR_TAG.match(token):
                if not stack or not isinstance(stack[-1], ForNode):
                    raise TemplateSyntaxError("endfor without matching for")
                stack.pop()
                continue

            # Check for malformed tags
            if token.startswith("{%") or token.startswith("{{"):
                raise TemplateSyntaxError(f"Invalid template tag: {token.strip()}")

            # Plain text
            if token:
                current_children().append(TextNode(text=token))

        # Check for unclosed blocks
        if stack:
            top = stack[-1]
            if isinstance(top, IfNode):
                raise TemplateSyntaxError("Unclosed if block")
            if isinstance(top, ForNode):
                raise TemplateSyntaxError("Unclosed for block")

        return nodes


# ─── Renderer ───


class TemplateRenderer:
    def __init__(self, filters: FilterRegistry, strict: bool = True) -> None:
        self._filters: FilterRegistry = filters
        self._strict: bool = strict

    def render(self, nodes: list[Node], context: dict[str, Any]) -> str:
        output: list[str] = []
        for node in nodes:
            output.append(self._render_node(node, context))
        return "".join(output)

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
        value: str = str(context[node.var_name])
        if node.filters:
            value = self._filters.apply(value, node.filters)
        return value

    def _render_if(self, node: IfNode, context: dict[str, Any]) -> str:
        condition_value: Any = self._evaluate_condition(node.condition, context)
        if condition_value:
            return self.render(node.true_branch, context)
        else:
            return self.render(node.false_branch, context)

    def _render_for(self, node: ForNode, context: dict[str, Any]) -> str:
        if node.iterable_name not in context:
            if self._strict:
                raise TemplateSyntaxError(
                    f"Undefined variable: {node.iterable_name}"
                )
            return ""
        iterable: Any = context[node.iterable_name]
        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(
                f"Variable '{node.iterable_name}' is not iterable"
            )
        output: list[str] = []
        for item in iterable:
            loop_context: dict[str, Any] = {**context, node.loop_var: item}
            output.append(self.render(node.body, loop_context))
        return "".join(output)

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> Any:
        # Simple condition evaluation: variable name truthiness or "not var"
        condition = condition.strip()
        if condition.startswith("not "):
            var_name: str = condition[4:].strip()
            value: Any = context.get(var_name, False)
            return not value
        # Direct variable lookup
        return context.get(condition, False)


# ─── Template Engine (Main Public API) ───


class TemplateEngine:
    def __init__(self, strict: bool = True) -> None:
        self._parser: TemplateParser = TemplateParser()
        self._filters: FilterRegistry = FilterRegistry()
        self._renderer: TemplateRenderer = TemplateRenderer(
            filters=self._filters, strict=strict
        )

    def render(self, template: str, context: dict[str, Any]) -> str:
        nodes: list[Node] = self._parser.parse(template)
        return self._renderer.render(nodes, context)

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters.register(name, func)


# ─── Demo ───

if __name__ == "__main__":
    engine = TemplateEngine(strict=True)

    template = """Hello, {{ name|upper }}!

{% if show_items %}Items:
{% for item in items %}- {{ item|capitalize }}
{% endfor %}{% else %}No items to display.{% endif %}
Total users: {{ count }}"""

    context: dict[str, Any] = {
        "name": "alice",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
        "count": 42,
    }

    result: str = engine.render(template, context)
    print(result)

    # Error handling demo
    print("\n--- Error handling ---")
    try:
        engine.render("{% if x %}unclosed", {"x": True})
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")

    try:
        engine.render("{{ unknown_var }}", {})
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")
