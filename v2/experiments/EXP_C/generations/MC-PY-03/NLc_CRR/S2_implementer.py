from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Union


# ─── Exceptions ───

class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""

    def __init__(self, message: str, line: int, column: int | None = None) -> None:
        self.message: str = message
        self.line: int = line
        self.column: int | None = column
        super().__init__(f"Line {line}: {message}")


# ─── AST Nodes ───

@dataclass
class TextNode:
    content: str


@dataclass
class VarNode:
    name: str
    filter_name: str | None = None


@dataclass
class IfNode:
    condition: str
    then_branch: list[ASTNode] = field(default_factory=list)
    else_branch: list[ASTNode] | None = None


@dataclass
class ForNode:
    var_name: str
    iterable: str
    body: list[ASTNode] = field(default_factory=list)


ASTNode = Union[TextNode, VarNode, IfNode, ForNode]


# ─── Regex Patterns ───

# Combined tokenizer pattern
TOKEN_PATTERN = re.compile(
    r"(\{\{.*?\}\})|(\{%.*?%\})",
    re.DOTALL,
)

# Variable: {{ var }} or {{ var | filter }}
VAR_PATTERN = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:\|\s*([a-zA-Z_][a-zA-Z0-9_]*))?\s*\}\}"
)

# Control tags
IF_START_PATTERN = re.compile(r"\{%\s*if\s+(.+?)\s*%\}")
ELSE_PATTERN = re.compile(r"\{%\s*else\s*%\}")
ENDIF_PATTERN = re.compile(r"\{%\s*endif\s*%\}")
FOR_START_PATTERN = re.compile(
    r"\{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*%\}"
)
ENDFOR_PATTERN = re.compile(r"\{%\s*endfor\s*%\}")


# ─── Built-in Filters ───

BUILTIN_FILTERS: dict[str, Callable[[Any], str]] = {
    "upper": lambda x: str(x).upper(),
    "lower": lambda x: str(x).lower(),
    "capitalize": lambda x: str(x).capitalize(),
    "strip": lambda x: str(x).strip(),
    "title": lambda x: str(x).title(),
    "length": lambda x: str(len(x)) if hasattr(x, "__len__") else "0",
    "default": lambda x: str(x) if x else "",
    "str": lambda x: str(x),
    "int": lambda x: str(int(x)) if x else "0",
}


# ─── Tokenizer ───

@dataclass
class Token:
    type: str  # TEXT, VAR, VAR_FILTER, IF_START, ELSE, IF_END, FOR_START, FOR_END
    content: str
    raw: str
    line: int


def _count_line(text: str, pos: int) -> int:
    """Count line number at position."""
    return text[:pos].count("\n") + 1


def tokenize(template: str) -> list[Token]:
    """Tokenize template string into a list of tokens."""
    tokens: list[Token] = []
    last_end: int = 0

    for match in TOKEN_PATTERN.finditer(template):
        start = match.start()
        end = match.end()

        # Text before this token
        if start > last_end:
            text = template[last_end:start]
            if text:
                tokens.append(Token("TEXT", text, text, _count_line(template, last_end)))

        raw = match.group(0)
        line = _count_line(template, start)

        # Variable tag
        var_m = VAR_PATTERN.match(raw)
        if var_m:
            if var_m.group(2):
                tokens.append(Token("VAR_FILTER", f"{var_m.group(1)}|{var_m.group(2)}", raw, line))
            else:
                tokens.append(Token("VAR", var_m.group(1), raw, line))
            last_end = end
            continue

        # Control tags
        if_m = IF_START_PATTERN.match(raw)
        if if_m:
            tokens.append(Token("IF_START", if_m.group(1), raw, line))
            last_end = end
            continue

        else_m = ELSE_PATTERN.match(raw)
        if else_m:
            tokens.append(Token("ELSE", "", raw, line))
            last_end = end
            continue

        endif_m = ENDIF_PATTERN.match(raw)
        if endif_m:
            tokens.append(Token("IF_END", "", raw, line))
            last_end = end
            continue

        for_m = FOR_START_PATTERN.match(raw)
        if for_m:
            tokens.append(Token("FOR_START", f"{for_m.group(1)}:{for_m.group(2)}", raw, line))
            last_end = end
            continue

        endfor_m = ENDFOR_PATTERN.match(raw)
        if endfor_m:
            tokens.append(Token("FOR_END", "", raw, line))
            last_end = end
            continue

        raise TemplateSyntaxError(f"Unknown tag: {raw}", line)

    # Remaining text
    if last_end < len(template):
        text = template[last_end:]
        if text:
            tokens.append(Token("TEXT", text, text, _count_line(template, last_end)))

    return tokens


# ─── Parser ───

def parse(tokens: list[Token]) -> list[ASTNode]:
    """Parse tokens into AST using stack-based approach."""
    root: list[ASTNode] = []
    stack: list[tuple[str, Any, list[ASTNode]]] = []
    current_children: list[ASTNode] = root

    for token in tokens:
        if token.type == "TEXT":
            current_children.append(TextNode(content=token.content))

        elif token.type == "VAR":
            current_children.append(VarNode(name=token.content))

        elif token.type == "VAR_FILTER":
            parts = token.content.split("|", 1)
            current_children.append(VarNode(name=parts[0], filter_name=parts[1]))

        elif token.type == "IF_START":
            node = IfNode(condition=token.content)
            stack.append(("if", node, current_children))
            current_children = node.then_branch

        elif token.type == "ELSE":
            if not stack or stack[-1][0] != "if":
                raise TemplateSyntaxError("Unexpected {% else %} without matching {% if %}", token.line)
            if_node: IfNode = stack[-1][1]
            if_node.else_branch = []
            current_children = if_node.else_branch

        elif token.type == "IF_END":
            if not stack or stack[-1][0] != "if":
                raise TemplateSyntaxError("Unexpected {% endif %} without matching {% if %}", token.line)
            _, completed_node, parent_children = stack.pop()
            parent_children.append(completed_node)
            current_children = parent_children

        elif token.type == "FOR_START":
            parts = token.content.split(":", 1)
            node = ForNode(var_name=parts[0], iterable=parts[1])
            stack.append(("for", node, current_children))
            current_children = node.body

        elif token.type == "FOR_END":
            if not stack or stack[-1][0] != "for":
                raise TemplateSyntaxError("Unexpected {% endfor %} without matching {% for %}", token.line)
            _, completed_node, parent_children = stack.pop()
            parent_children.append(completed_node)
            current_children = parent_children

    if stack:
        tag_type = stack[-1][0]
        raise TemplateSyntaxError(f"Unclosed {{% {tag_type} %}} tag", 0)

    return root


# ─── Evaluator ───

def _resolve_var(name: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted variable name from context."""
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


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a simple condition expression safely."""
    condition = condition.strip()

    # Handle 'not' prefix
    if condition.startswith("not "):
        return not _evaluate_condition(condition[4:], context)

    # Handle comparison operators
    for op, func in [
        ("==", lambda a, b: a == b),
        ("!=", lambda a, b: a != b),
        (">=", lambda a, b: a >= b),
        ("<=", lambda a, b: a <= b),
        (">", lambda a, b: a > b),
        ("<", lambda a, b: a < b),
    ]:
        if op in condition:
            left, right = condition.split(op, 1)
            left_val = _resolve_var(left.strip(), context)
            right_str = right.strip().strip("'\"")
            # Try numeric comparison
            try:
                right_val: Any = int(right_str)
            except ValueError:
                try:
                    right_val = float(right_str)
                except ValueError:
                    right_val = right_str
            return func(left_val, right_val)

    # Simple truthiness
    value = _resolve_var(condition, context)
    return bool(value)


def render_nodes(nodes: list[ASTNode], context: dict[str, Any], filters: dict[str, Callable[[Any], str]]) -> str:
    """Render AST nodes to string."""
    output: list[str] = []

    for node in nodes:
        if isinstance(node, TextNode):
            output.append(node.content)

        elif isinstance(node, VarNode):
            value = _resolve_var(node.name, context)
            if value is None:
                value = ""
            if node.filter_name:
                filt = filters.get(node.filter_name)
                if filt:
                    value = filt(value)
                else:
                    value = str(value)
            else:
                value = str(value)
            output.append(value)

        elif isinstance(node, IfNode):
            if _evaluate_condition(node.condition, context):
                output.append(render_nodes(node.then_branch, context, filters))
            elif node.else_branch is not None:
                output.append(render_nodes(node.else_branch, context, filters))

        elif isinstance(node, ForNode):
            iterable = _resolve_var(node.iterable, context)
            if iterable and hasattr(iterable, "__iter__"):
                for item in iterable:
                    loop_context = {**context, node.var_name: item}
                    output.append(render_nodes(node.body, loop_context, filters))

    return "".join(output)


# ─── Template Engine ───

class TemplateEngine:
    """Template engine with variable substitution, filters, conditionals, and loops."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[Any], str]] = dict(BUILTIN_FILTERS)

    def register_filter(self, name: str, func: Callable[[Any], str]) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Render a template string with the given context."""
        ctx = context or {}
        tokens = tokenize(template)
        ast = parse(tokens)
        return render_nodes(ast, ctx, self._filters)

    def render_file(self, file_path: str, context: dict[str, Any] | None = None) -> str:
        """Render a template from file."""
        with open(file_path, "r", encoding="utf-8") as f:
            template = f.read()
        return self.render(template, context)


# ─── Demo / Main ───

if __name__ == "__main__":
    engine = TemplateEngine()

    # Register custom filter
    engine.register_filter("reverse", lambda x: str(x)[::-1])

    # Basic variable substitution
    result = engine.render("Hello, {{ name }}!", {"name": "World"})
    print(result)  # Hello, World!

    # Filter
    result = engine.render("{{ name | upper }}", {"name": "alice"})
    print(result)  # ALICE

    # Conditional
    template = "{% if show %}Visible{% else %}Hidden{% endif %}"
    print(engine.render(template, {"show": True}))   # Visible
    print(engine.render(template, {"show": False}))   # Hidden

    # Loop
    template = "{% for item in items %}{{ item }}, {% endfor %}"
    print(engine.render(template, {"items": ["a", "b", "c"]}))  # a, b, c,

    # Nested
    template = """{% for user in users %}
{% if user.active %}Active: {{ user.name | upper }}
{% endif %}{% endfor %}"""
    context = {
        "users": [
            {"name": "alice", "active": True},
            {"name": "bob", "active": False},
            {"name": "carol", "active": True},
        ]
    }
    print(engine.render(template, context))

    # Error handling
    try:
        engine.render("{% if x %}no end")
    except TemplateSyntaxError as e:
        print(f"Error: {e}")
