"""Template Engine — regex-based parsing, variable substitution, conditionals, loops, filters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union

# ─── Exceptions ───────────────────────────────────────────────────────────────

class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        if self.line is not None:
            return f"Template syntax error at line {self.line}: {self.message}"
        return f"Template syntax error: {self.message}"


# ─── Token Types ──────────────────────────────────────────────────────────────

class TokenType(Enum):
    TEXT = auto()
    VARIABLE = auto()
    IF_START = auto()
    IF_END = auto()
    FOR_START = auto()
    FOR_END = auto()
    ELSE = auto()


@dataclass
class Token:
    type: TokenType
    content: str
    var_name: Optional[str] = None
    filter_names: Optional[List[str]] = None
    loop_var: Optional[str] = None
    loop_iterable: Optional[str] = None


# ─── AST Nodes ────────────────────────────────────────────────────────────────

@dataclass
class TextNode:
    content: str


@dataclass
class VariableNode:
    name: str
    filters: List[str]


@dataclass
class IfNode:
    condition: str
    body: List[Any]  # List of AST nodes
    else_body: List[Any]


@dataclass
class ForNode:
    var: str
    iterable: str
    body: List[Any]


ASTNode = Union[TextNode, VariableNode, IfNode, ForNode]


# ─── Regex Patterns ──────────────────────────────────────────────────────────

class TemplatePatterns:
    # Variable: {{ var }} or {{ var|filter1|filter2 }}
    VARIABLE = re.compile(r'\{\{\s*(\w+(?:\.\w+)*)((?:\s*\|\s*\w+)*)\s*\}\}')

    # If block: {% if condition %}
    IF_START = re.compile(r'\{%\s*if\s+(\w+)\s*%\}')
    IF_END = re.compile(r'\{%\s*endif\s*%\}')
    ELSE = re.compile(r'\{%\s*else\s*%\}')

    # For block: {% for item in list %}
    FOR_START = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    FOR_END = re.compile(r'\{%\s*endfor\s*%\}')

    # Combined tag pattern
    TAG = re.compile(r'(\{\{[^}]+\}\}|\{%[^%]+%\})')


# ─── Filter Registry ─────────────────────────────────────────────────────────

class FilterRegistry:
    """Registry of available template filters."""

    def __init__(self) -> None:
        self._filters: Dict[str, Callable[[Any], str]] = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "capitalize": lambda x: str(x).capitalize(),
            "title": lambda x: str(x).title(),
            "strip": lambda x: str(x).strip(),
            "length": lambda x: str(len(x)) if hasattr(x, "__len__") else "0",
            "default": lambda x: str(x) if x else "",
            "reverse": lambda x: str(x)[::-1],
        }

    def register(self, name: str, func: Callable[[Any], str]) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    def apply(self, name: str, value: Any) -> str:
        """Apply a filter to a value."""
        if name not in self._filters:
            raise TemplateSyntaxError(f"Unknown filter: '{name}'")
        return self._filters[name](value)

    def has_filter(self, name: str) -> bool:
        """Check if a filter exists."""
        return name in self._filters


# ─── Tokenizer ────────────────────────────────────────────────────────────────

class Tokenizer:
    """Tokenize a template string into structured tokens."""

    def tokenize(self, template: str) -> List[Token]:
        tokens: List[Token] = []
        pos = 0

        for match in TemplatePatterns.TAG.finditer(template):
            # Text before tag
            if match.start() > pos:
                text = template[pos:match.start()]
                if text:
                    tokens.append(Token(TokenType.TEXT, text))

            tag = match.group(1)
            token = self._parse_tag(tag)
            if token:
                tokens.append(token)

            pos = match.end()

        # Remaining text
        if pos < len(template):
            text = template[pos:]
            if text:
                tokens.append(Token(TokenType.TEXT, text))

        return tokens

    def _parse_tag(self, tag: str) -> Optional[Token]:
        # Variable
        var_match = TemplatePatterns.VARIABLE.match(tag)
        if var_match:
            var_name = var_match.group(1)
            filter_str = var_match.group(2).strip()
            filters = [f.strip() for f in filter_str.split("|") if f.strip()] if filter_str else []
            return Token(TokenType.VARIABLE, tag, var_name=var_name, filter_names=filters)

        # If start
        if_match = TemplatePatterns.IF_START.match(tag)
        if if_match:
            return Token(TokenType.IF_START, tag, var_name=if_match.group(1))

        # If end
        if TemplatePatterns.IF_END.match(tag):
            return Token(TokenType.IF_END, tag)

        # Else
        if TemplatePatterns.ELSE.match(tag):
            return Token(TokenType.ELSE, tag)

        # For start
        for_match = TemplatePatterns.FOR_START.match(tag)
        if for_match:
            return Token(
                TokenType.FOR_START,
                tag,
                loop_var=for_match.group(1),
                loop_iterable=for_match.group(2),
            )

        # For end
        if TemplatePatterns.FOR_END.match(tag):
            return Token(TokenType.FOR_END, tag)

        return None


# ─── Parser ───────────────────────────────────────────────────────────────────

class Parser:
    """Parse tokens into an AST using a stack-based approach."""

    def parse(self, tokens: List[Token]) -> List[ASTNode]:
        root: List[ASTNode] = []
        stack: List[dict] = []  # {node, section}
        current_body: List[ASTNode] = root

        for token in tokens:
            if token.type == TokenType.TEXT:
                current_body.append(TextNode(token.content))

            elif token.type == TokenType.VARIABLE:
                current_body.append(
                    VariableNode(
                        name=token.var_name or "",
                        filters=token.filter_names or [],
                    )
                )

            elif token.type == TokenType.IF_START:
                if_node = IfNode(
                    condition=token.var_name or "",
                    body=[],
                    else_body=[],
                )
                current_body.append(if_node)
                stack.append({"node": if_node, "section": "body"})
                current_body = if_node.body

            elif token.type == TokenType.ELSE:
                if not stack or not isinstance(stack[-1]["node"], IfNode):
                    raise TemplateSyntaxError("Unexpected {% else %} outside of if block")
                stack[-1]["section"] = "else_body"
                current_body = stack[-1]["node"].else_body

            elif token.type == TokenType.IF_END:
                if not stack or not isinstance(stack[-1]["node"], IfNode):
                    raise TemplateSyntaxError("Unexpected {% endif %} without matching {% if %}")
                stack.pop()
                if stack:
                    section = stack[-1]["section"]
                    node = stack[-1]["node"]
                    current_body = getattr(node, section)
                else:
                    current_body = root

            elif token.type == TokenType.FOR_START:
                for_node = ForNode(
                    var=token.loop_var or "",
                    iterable=token.loop_iterable or "",
                    body=[],
                )
                current_body.append(for_node)
                stack.append({"node": for_node, "section": "body"})
                current_body = for_node.body

            elif token.type == TokenType.FOR_END:
                if not stack or not isinstance(stack[-1]["node"], ForNode):
                    raise TemplateSyntaxError("Unexpected {% endfor %} without matching {% for %}")
                stack.pop()
                if stack:
                    section = stack[-1]["section"]
                    node = stack[-1]["node"]
                    current_body = getattr(node, section)
                else:
                    current_body = root

        if stack:
            node = stack[-1]["node"]
            if isinstance(node, IfNode):
                raise TemplateSyntaxError("Unclosed {% if %} block")
            elif isinstance(node, ForNode):
                raise TemplateSyntaxError("Unclosed {% for %} block")
            else:
                raise TemplateSyntaxError("Unclosed block")

        return root


# ─── Renderer ─────────────────────────────────────────────────────────────────

class Renderer:
    """Render an AST given a context dictionary."""

    def __init__(self, filters: FilterRegistry) -> None:
        self.filters = filters

    def render(self, nodes: List[ASTNode], context: Dict[str, Any]) -> str:
        parts: List[str] = []

        for node in nodes:
            if isinstance(node, TextNode):
                parts.append(node.content)

            elif isinstance(node, VariableNode):
                value = self._resolve_variable(node.name, context)
                for filter_name in node.filters:
                    value = self.filters.apply(filter_name, value)
                parts.append(str(value) if value is not None else "")

            elif isinstance(node, IfNode):
                condition_value = self._resolve_variable(node.condition, context)
                if self._is_truthy(condition_value):
                    parts.append(self.render(node.body, context))
                else:
                    parts.append(self.render(node.else_body, context))

            elif isinstance(node, ForNode):
                iterable = self._resolve_variable(node.iterable, context)
                if iterable and hasattr(iterable, "__iter__"):
                    for item in iterable:
                        child_context = {**context, node.var: item}
                        parts.append(self.render(node.body, child_context))

        return "".join(parts)

    def _resolve_variable(self, name: str, context: Dict[str, Any]) -> Any:
        parts = name.split(".")
        value: Any = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        return value

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return True


# ─── Template Engine ──────────────────────────────────────────────────────────

class TemplateEngine:
    """
    Template engine supporting variable substitution, conditionals, loops, and filters.

    Template syntax:
    - Variables: {{ name }} or {{ name|upper }}
    - Conditionals: {% if var %}...{% else %}...{% endif %}
    - Loops: {% for item in items %}...{% endfor %}
    - Filters: {{ name|upper|strip }}
    """

    def __init__(self) -> None:
        self.filters = FilterRegistry()
        self._tokenizer = Tokenizer()
        self._parser = Parser()
        self._renderer = Renderer(self.filters)

    def render(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template string with the given context.

        Args:
            template: The template string.
            context: Dictionary of variables available in the template.

        Returns:
            Rendered string.

        Raises:
            TemplateSyntaxError: If the template has syntax errors.
        """
        ctx = context or {}
        tokens = self._tokenizer.tokenize(template)
        ast_nodes = self._parser.parse(tokens)
        return self._renderer.render(ast_nodes, ctx)

    def register_filter(self, name: str, func: Callable[[Any], str]) -> None:
        """
        Register a custom filter.

        Args:
            name: Filter name to use in templates.
            func: Callable that transforms a value to a string.
        """
        self.filters.register(name, func)

    def validate(self, template: str) -> None:
        """
        Validate template syntax without rendering.

        Args:
            template: The template string to validate.

        Raises:
            TemplateSyntaxError: If the template has syntax errors.
        """
        tokens = self._tokenizer.tokenize(template)
        self._parser.parse(tokens)


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    # Register custom filter
    engine.register_filter("exclaim", lambda x: f"{x}!")

    # Test template
    template = """Hello, {{ name|upper }}!

{% if show_items %}Items:
{% for item in items %}- {{ item|capitalize }}
{% endfor %}{% else %}No items to show.
{% endif %}
Total users: {{ count }}"""

    context = {
        "name": "world",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
        "count": 42,
    }

    result = engine.render(template, context)
    print(result)

    # Test validation
    try:
        engine.validate("{% if x %}unclosed")
    except TemplateSyntaxError as e:
        print(f"\nValidation error: {e}")
