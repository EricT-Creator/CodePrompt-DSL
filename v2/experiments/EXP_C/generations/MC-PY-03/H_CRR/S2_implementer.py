"""
MC-PY-03: Template Engine
[L]PY310 [D]STDLIB_ONLY [!D]NO_TMPL_LIB [PARSE]REGEX [!D]NO_AST [TYPE]FULL_HINTS [ERR]SYNTAX_EXC [O]CLASS [FILE]SINGLE
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Exceptions ───────────────────────────────────────────────────────────────

class TemplateSyntaxError(Exception):
    """Raised for template syntax errors."""

    def __init__(self, message: str, line: int | None = None, col: int | None = None) -> None:
        self.message: str = message
        self.line: int | None = line
        self.col: int | None = col
        super().__init__(self._format())

    def _format(self) -> str:
        loc: str = f" at line {self.line}, col {self.col}" if self.line else ""
        return f"Template syntax error{loc}: {self.message}"


class TemplateRuntimeError(Exception):
    """Raised during template rendering."""
    pass


# ─── Regex Patterns ──────────────────────────────────────────────────────────

VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:\|\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\s*\|\s*[a-zA-Z_][a-zA-Z0-9_]*)*))?\s*\}\}"
)

IF_PATTERN: re.Pattern[str] = re.compile(
    r"\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*endif\s*%\}",
    re.DOTALL,
)

IF_ELSE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}",
    re.DOTALL,
)

FOR_PATTERN: re.Pattern[str] = re.compile(
    r"\{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*%\}"
    r"(.*?)"
    r"\{%\s*endfor\s*%\}",
    re.DOTALL,
)

COMMENT_PATTERN: re.Pattern[str] = re.compile(
    r"\{#.*?#\}",
    re.DOTALL,
)


# ─── Built-in Filters ────────────────────────────────────────────────────────

FILTERS: dict[str, Callable[[Any], str]] = {
    "upper": lambda x: str(x).upper(),
    "lower": lambda x: str(x).lower(),
    "capitalize": lambda x: str(x).capitalize(),
    "trim": lambda x: str(x).strip(),
    "title": lambda x: str(x).title(),
    "length": lambda x: str(len(x)) if hasattr(x, "__len__") else "0",
    "default": lambda x: str(x) if x else "",
    "reverse": lambda x: str(x)[::-1] if isinstance(x, str) else str(list(reversed(x))) if isinstance(x, list) else str(x),
}


def apply_filter(value: Any, filter_name: str) -> str:
    """Apply a named filter to a value."""
    fn: Callable[[Any], str] | None = FILTERS.get(filter_name)
    if fn is None:
        raise TemplateSyntaxError(f"Unknown filter: '{filter_name}'")
    return fn(value)


def apply_filters(value: Any, filter_chain: list[str]) -> str:
    """Apply a chain of filters to a value."""
    result: Any = value
    for f in filter_chain:
        result = apply_filter(result, f.strip())
    return str(result)


# ─── Context Helpers ──────────────────────────────────────────────────────────

def resolve_variable(name: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted variable name from context."""
    parts: list[str] = name.split(".")
    current: Any = context

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            raise TemplateRuntimeError(f"Variable '{name}' not defined")

    return current


def eval_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a simple condition string against context."""
    condition = condition.strip()

    # Handle 'not' prefix
    if condition.startswith("not "):
        return not eval_condition(condition[4:], context)

    # Handle comparison operators
    for op, fn in [
        ("==", lambda a, b: a == b),
        ("!=", lambda a, b: a != b),
        (">=", lambda a, b: a >= b),
        ("<=", lambda a, b: a <= b),
        (">", lambda a, b: a > b),
        ("<", lambda a, b: a < b),
    ]:
        if op in condition:
            left_str, right_str = condition.split(op, 1)
            left: Any = _resolve_value(left_str.strip(), context)
            right: Any = _resolve_value(right_str.strip(), context)
            return fn(left, right)

    # Simple truthiness check
    try:
        value: Any = resolve_variable(condition, context)
        return bool(value)
    except TemplateRuntimeError:
        return False


def _resolve_value(token: str, context: dict[str, Any]) -> Any:
    """Resolve a value token — could be a variable, string literal, or number."""
    # String literal
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    # Integer
    try:
        return int(token)
    except ValueError:
        pass
    # Float
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
    return resolve_variable(token, context)


# ─── Template Engine ──────────────────────────────────────────────────────────

@dataclass
class TemplateEngine:
    """Regex-based template engine with variables, conditionals, loops, and filters."""

    template: str

    def render(self, context: dict[str, Any] | None = None) -> str:
        """Render template with the given context."""
        ctx: dict[str, Any] = context or {}
        return self._render(self.template, ctx)

    def _render(self, template: str, context: dict[str, Any]) -> str:
        """Internal recursive rendering."""
        result: str = template

        # 1. Strip comments
        result = COMMENT_PATTERN.sub("", result)

        # 2. Process for loops (innermost first via repeated passes)
        max_iterations: int = 100
        iteration: int = 0
        while FOR_PATTERN.search(result) and iteration < max_iterations:
            result = self._process_for_loops(result, context)
            iteration += 1

        # 3. Process if/else blocks (innermost first)
        iteration = 0
        while IF_ELSE_PATTERN.search(result) or IF_PATTERN.search(result):
            if iteration >= max_iterations:
                break
            result = self._process_conditionals(result, context)
            iteration += 1

        # 4. Substitute variables
        result = self._process_variables(result, context)

        return result

    def _process_for_loops(self, template: str, context: dict[str, Any]) -> str:
        """Process {% for item in list %} ... {% endfor %} blocks."""

        def replace_for(match: re.Match[str]) -> str:
            var_name: str = match.group(1)
            list_name: str = match.group(2)
            body: str = match.group(3)

            try:
                iterable: Any = resolve_variable(list_name, context)
            except TemplateRuntimeError:
                return ""

            if not hasattr(iterable, "__iter__"):
                return ""

            parts: list[str] = []
            items: list[Any] = list(iterable)
            for idx, item in enumerate(items):
                loop_ctx: dict[str, Any] = {
                    **context,
                    var_name: item,
                    "loop": {
                        "index": idx + 1,
                        "index0": idx,
                        "first": idx == 0,
                        "last": idx == len(items) - 1,
                        "length": len(items),
                    },
                }
                parts.append(self._render(body, loop_ctx))
            return "".join(parts)

        return FOR_PATTERN.sub(replace_for, template)

    def _process_conditionals(self, template: str, context: dict[str, Any]) -> str:
        """Process {% if %} ... {% else %} ... {% endif %} blocks."""

        # Try if/else first
        def replace_if_else(match: re.Match[str]) -> str:
            condition: str = match.group(1)
            true_body: str = match.group(2)
            false_body: str = match.group(3)

            if eval_condition(condition, context):
                return self._render(true_body, context)
            return self._render(false_body, context)

        result: str = IF_ELSE_PATTERN.sub(replace_if_else, template)

        # Then plain if
        def replace_if(match: re.Match[str]) -> str:
            condition: str = match.group(1)
            body: str = match.group(2)

            if eval_condition(condition, context):
                return self._render(body, context)
            return ""

        result = IF_PATTERN.sub(replace_if, result)

        return result

    def _process_variables(self, template: str, context: dict[str, Any]) -> str:
        """Process {{ variable | filter }} substitutions."""

        def replace_var(match: re.Match[str]) -> str:
            var_name: str = match.group(1)
            filter_str: str | None = match.group(2)

            try:
                value: Any = resolve_variable(var_name, context)
            except TemplateRuntimeError:
                return ""

            if filter_str:
                filter_names: list[str] = [f.strip() for f in filter_str.split("|")]
                return apply_filters(value, filter_names)

            return str(value)

        return VARIABLE_PATTERN.sub(replace_var, template)


# ─── Demo ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Variable substitution
    engine1 = TemplateEngine("Hello, {{ name | upper }}!")
    print(engine1.render({"name": "world"}))

    # Conditionals
    engine2 = TemplateEngine("{% if logged_in %}Welcome back!{% else %}Please log in.{% endif %}")
    print(engine2.render({"logged_in": True}))
    print(engine2.render({"logged_in": False}))

    # For loops
    engine3 = TemplateEngine(
        "Items: {% for item in items %}{{ item }}{% if not loop.last %}, {% endif %}{% endfor %}"
    )
    print(engine3.render({"items": ["apple", "banana", "cherry"]}))

    # Nested
    engine4 = TemplateEngine(
        "{% for user in users %}{{ user.name | capitalize }}: {% for role in user.roles %}{{ role }}{% if not loop.last %}, {% endif %}{% endfor %}\n{% endfor %}"
    )
    print(engine4.render({
        "users": [
            {"name": "alice", "roles": ["admin", "editor"]},
            {"name": "bob", "roles": ["viewer"]},
        ]
    }))


if __name__ == "__main__":
    main()
