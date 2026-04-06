"""Template Engine — MC-PY-03 (H × RRR)"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# ── Custom Exception ──
class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line: int | None = line
        prefix: str = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")

# ── Regex Patterns ──
VAR_PATTERN: re.Pattern[str] = re.compile(r"\{\{\s*(\w+(?:\|\w+)*)\s*\}\}")
IF_OPEN: re.Pattern[str] = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ELSE_TAG: re.Pattern[str] = re.compile(r"\{%\s*else\s*%\}")
ENDIF_TAG: re.Pattern[str] = re.compile(r"\{%\s*endif\s*%\}")
FOR_OPEN: re.Pattern[str] = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
ENDFOR_TAG: re.Pattern[str] = re.compile(r"\{%\s*endfor\s*%\}")
TOKEN_PATTERN: re.Pattern[str] = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)

# ── AST Node Types ──
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

@dataclass
class RootNode:
    children: list[Node] = field(default_factory=list)

# ── Filter Registry ──
class FilterRegistry:
    def __init__(self) -> None:
        self._filters: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func

    def apply(self, value: str, filter_names: list[str]) -> str:
        result: str = value
        for name in filter_names:
            if name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {name}")
            result = self._filters[name](result)
        return result

# ── Parser ──
class TemplateParser:
    def __init__(self) -> None:
        pass

    def parse(self, template: str) -> RootNode:
        tokens: list[str] = TOKEN_PATTERN.split(template)
        root: RootNode = RootNode()
        stack: list[RootNode | IfNode | ForNode] = [root]

        for token in tokens:
            if not token:
                continue

            # Check if it's a template tag
            if token.startswith("{{") and token.endswith("}}"):
                node: VarNode = self._parse_var(token)
                self._current_children(stack).append(node)

            elif token.startswith("{%") and token.endswith("%}"):
                self._parse_block_tag(token, stack)

            else:
                # Plain text
                if token:
                    self._current_children(stack).append(TextNode(text=token))

        # Check for unclosed blocks
        if len(stack) > 1:
            top = stack[-1]
            if isinstance(top, IfNode):
                raise TemplateSyntaxError("Unclosed if block")
            elif isinstance(top, ForNode):
                raise TemplateSyntaxError("Unclosed for block")
            else:
                raise TemplateSyntaxError("Unclosed block")

        return root

    def _parse_var(self, token: str) -> VarNode:
        match: re.Match[str] | None = VAR_PATTERN.match(token)
        if not match:
            raise TemplateSyntaxError(f"Invalid variable tag: {token}")

        content: str = match.group(1)
        parts: list[str] = content.split("|")
        var_name: str = parts[0]
        filters: list[str] = parts[1:]

        return VarNode(var_name=var_name, filters=filters)

    def _parse_block_tag(self, token: str, stack: list[RootNode | IfNode | ForNode]) -> None:
        # Try matching each block tag type
        if_match: re.Match[str] | None = IF_OPEN.match(token)
        if if_match:
            condition: str = if_match.group(1).strip()
            node: IfNode = IfNode(condition=condition, true_branch=[], false_branch=[])
            self._current_children(stack).append(node)
            stack.append(node)
            return

        if ELSE_TAG.match(token):
            if not stack or not isinstance(stack[-1], IfNode):
                raise TemplateSyntaxError("else without matching if")
            # Switch to false branch — handled by _current_children logic
            # We mark the IfNode to know we're in the else branch
            if_node: IfNode = stack[-1]  # type: ignore
            # Use a sentinel: store a flag on the node
            if not hasattr(if_node, "_in_else"):
                if_node._in_else = True  # type: ignore
            return

        if ENDIF_TAG.match(token):
            if not stack or not isinstance(stack[-1], IfNode):
                raise TemplateSyntaxError("endif without matching if")
            stack.pop()
            return

        for_match: re.Match[str] | None = FOR_OPEN.match(token)
        if for_match:
            loop_var: str = for_match.group(1)
            iterable_name: str = for_match.group(2)
            for_node: ForNode = ForNode(loop_var=loop_var, iterable_name=iterable_name, body=[])
            self._current_children(stack).append(for_node)
            stack.append(for_node)
            return

        if ENDFOR_TAG.match(token):
            if not stack or not isinstance(stack[-1], ForNode):
                raise TemplateSyntaxError("endfor without matching for")
            stack.pop()
            return

        raise TemplateSyntaxError(f"Invalid template tag: {token}")

    def _current_children(self, stack: list[RootNode | IfNode | ForNode]) -> list[Node]:
        top = stack[-1]
        if isinstance(top, RootNode):
            return top.children
        elif isinstance(top, IfNode):
            if hasattr(top, "_in_else") and top._in_else:  # type: ignore
                return top.false_branch
            return top.true_branch
        elif isinstance(top, ForNode):
            return top.body
        return []

# ── Renderer ──
class TemplateRenderer:
    def __init__(self, filter_registry: FilterRegistry, strict: bool = True) -> None:
        self._filters: FilterRegistry = filter_registry
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

        elif isinstance(node, VarNode):
            return self._render_var(node, context)

        elif isinstance(node, IfNode):
            return self._render_if(node, context)

        elif isinstance(node, ForNode):
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
        condition_result: bool = self._evaluate_condition(node.condition, context)

        if condition_result:
            return self._render_nodes(node.true_branch, context)
        else:
            return self._render_nodes(node.false_branch, context)

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a simple condition expression against context."""
        condition = condition.strip()

        # Handle "not" prefix
        if condition.startswith("not "):
            return not self._evaluate_condition(condition[4:], context)

        # Handle comparison operators
        for op in ("==", "!=", ">=", "<=", ">", "<"):
            if op in condition:
                left_str, right_str = condition.split(op, 1)
                left: Any = self._resolve_value(left_str.strip(), context)
                right: Any = self._resolve_value(right_str.strip(), context)
                if op == "==":
                    return left == right
                elif op == "!=":
                    return left != right
                elif op == ">=":
                    return left >= right
                elif op == "<=":
                    return left <= right
                elif op == ">":
                    return left > right
                elif op == "<":
                    return left < right

        # Simple truthiness check
        value: Any = self._resolve_value(condition, context)
        return bool(value)

    def _resolve_value(self, token: str, context: dict[str, Any]) -> Any:
        token = token.strip()

        # String literal
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            return token[1:-1]

        # Number
        try:
            if "." in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        # Boolean literals
        if token == "True":
            return True
        if token == "False":
            return False
        if token == "None":
            return None

        # Context variable
        return context.get(token, None)

    def _render_for(self, node: ForNode, context: dict[str, Any]) -> str:
        iterable: Any = context.get(node.iterable_name)
        if iterable is None:
            if self._strict:
                raise TemplateSyntaxError(f"Undefined variable: {node.iterable_name}")
            return ""

        if not hasattr(iterable, "__iter__"):
            raise TemplateSyntaxError(f"Variable '{node.iterable_name}' is not iterable")

        parts: list[str] = []
        for item in iterable:
            loop_context: dict[str, Any] = {**context, node.loop_var: item}
            parts.append(self._render_nodes(node.body, loop_context))

        return "".join(parts)

# ── Template Engine (Public API) ──
class TemplateEngine:
    def __init__(self, strict: bool = True) -> None:
        self._parser: TemplateParser = TemplateParser()
        self._filter_registry: FilterRegistry = FilterRegistry()
        self._renderer: TemplateRenderer = TemplateRenderer(self._filter_registry, strict=strict)

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        root: RootNode = self._parser.parse(template)
        return self._renderer.render(root, context or {})

    def register_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filter_registry.register_filter(name, func)


# ── Main (demo) ──
if __name__ == "__main__":
    engine = TemplateEngine(strict=False)

    # Variable substitution
    result: str = engine.render("Hello, {{ name }}!", {"name": "World"})
    print(result)  # Hello, World!

    # Filters
    result = engine.render("{{ name|upper }}", {"name": "alice"})
    print(result)  # ALICE

    # Chained filters
    result = engine.render("{{ name|upper|capitalize }}", {"name": "hello world"})
    print(result)  # Hello world  (upper → HELLO WORLD → capitalize → Hello world)

    # Conditionals
    tmpl: str = "{% if show %}Visible{% else %}Hidden{% endif %}"
    print(engine.render(tmpl, {"show": True}))   # Visible
    print(engine.render(tmpl, {"show": False}))   # Hidden

    # Loops
    tmpl = "{% for item in items %}[{{ item }}]{% endfor %}"
    print(engine.render(tmpl, {"items": ["a", "b", "c"]}))  # [a][b][c]

    # Nested
    tmpl = "{% for user in users %}{% if user %}{{ user|upper }} {% endif %}{% endfor %}"
    print(engine.render(tmpl, {"users": ["alice", "", "bob"]}))  # ALICE BOB
