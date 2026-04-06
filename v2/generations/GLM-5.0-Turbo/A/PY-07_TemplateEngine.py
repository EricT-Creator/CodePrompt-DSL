import re
from typing import Any, Dict


class TemplateSyntaxError(Exception):
    """Raised when a template has syntax errors."""
    pass


def render(template: str, context: Dict[str, Any]) -> str:
    """Render a template string with the given context.

    Supports:
      - Variable substitution: {{variable}}
      - Filter pipes: {{variable|upper}}, {{variable|lower}}, {{variable|title}}
      - Conditional blocks: {% if condition %}...{% endif %}
      - For loops: {% for item in list %}...{% endfor %}
      - Nested blocks (if inside for, etc.)

    Raises TemplateSyntaxError for malformed templates.
    """
    tokens = tokenize(template)
    result = _render_tokens(tokens, context)
    return result


# --- Tokenizer ---

class Token:
    TEXT = "text"
    VAR = "var"
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    ENDIF = "endif"
    FOR = "for"
    ENDFOR = "endfor"

    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def tokenize(template: str) -> list:
    """Parse template string into a list of tokens."""
    tokens = []
    # Pattern matches {{ ... }}, {% ... %}, and plain text
    pattern = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})")

    pos = 0
    for match in pattern.finditer(template):
        start, end = match.span()

        # Text before this tag
        if start > pos:
            tokens.append(Token(Token.TEXT, template[pos:start]))

        tag = match.group(1)

        if tag.startswith("{{") and tag.endswith("}}"):
            expr = tag[2:-2].strip()
            if not expr:
                raise TemplateSyntaxError(f"Empty variable expression at position {start}")
            tokens.append(Token(Token.VAR, expr))

        elif tag.startswith("{%") and tag.endswith("%}"):
            expr = tag[2:-2].strip()
            if expr.startswith("if ") or expr.startswith("if\t"):
                condition = expr[3:].strip()
                if not condition:
                    raise TemplateSyntaxError(f"Empty if condition at position {start}")
                tokens.append(Token(Token.IF, condition))
            elif expr.startswith("elif ") or expr.startswith("elif\t"):
                condition = expr[5:].strip()
                if not condition:
                    raise TemplateSyntaxError(f"Empty elif condition at position {start}")
                tokens.append(Token(Token.ELIF, condition))
            elif expr == "else":
                tokens.append(Token(Token.ELSE, ""))
            elif expr == "endif":
                tokens.append(Token(Token.ENDIF, ""))
            elif expr.startswith("for "):
                for_match = re.match(r"for\s+(\w+)\s+in\s+(.+)", expr)
                if not for_match:
                    raise TemplateSyntaxError(
                        f"Invalid for syntax '{expr}' at position {start}. Expected: for item in list"
                    )
                tokens.append(Token(Token.FOR, for_match.group(1) + "|" + for_match.group(2).strip()))
            elif expr == "endfor":
                tokens.append(Token(Token.ENDFOR, ""))
            else:
                raise TemplateSyntaxError(
                    f"Unknown template tag '{expr}' at position {start}"
                )
        else:
            raise TemplateSyntaxError(f"Malformed tag at position {start}: {tag}")

        pos = end

    # Remaining text
    if pos < len(template):
        tokens.append(Token(Token.TEXT, template[pos:]))

    return tokens


# --- Renderer ---

def _resolve_variable(expr: str, context: Dict[str, Any]) -> Any:
    """Resolve a variable expression, supporting dot notation and filter pipes."""
    filters = {
        "upper": lambda x: str(x).upper(),
        "lower": lambda x: str(x).lower(),
        "title": lambda x: str(x).title(),
    }

    # Split by pipe for filters
    parts = expr.split("|")
    var_expr = parts[0].strip()
    filter_chain = [p.strip() for p in parts[1:]]

    # Resolve dot notation
    value = _resolve_dotted(var_expr, context)

    # Apply filters
    for f in filter_chain:
        if f not in filters:
            raise TemplateSyntaxError(f"Unknown filter '{f}'")
        value = filters[f](value)

    return value


def _resolve_dotted(expr: str, context: Dict[str, Any]) -> Any:
    """Resolve a dotted variable path like 'user.name'."""
    parts = expr.split(".")
    value = context
    for part in parts:
        if isinstance(value, dict):
            if part not in value:
                return ""
            value = value[part]
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            return ""
    return value


def _eval_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a simple condition expression."""
    condition = condition.strip()

    # Handle 'not' prefix
    if condition.startswith("not "):
        return not _eval_condition(condition[4:], context)

    # Handle 'in' operator: "x in y"
    in_match = re.match(r"(.+?)\s+in\s+(.+)", condition)
    if in_match:
        left = _resolve_dotted(in_match.group(1).strip(), context)
        right = _resolve_dotted(in_match.group(2).strip(), context)
        return left in right

    # Simple boolean value
    value = _resolve_dotted(condition, context)
    return bool(value)


def _render_tokens(tokens: list, context: Dict[str, Any]) -> str:
    """Render a flat list of tokens with context, handling control flow."""
    output = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == Token.TEXT:
            output.append(token.value)
            i += 1

        elif token.type == Token.VAR:
            value = _resolve_variable(token.value, context)
            output.append(str(value))
            i += 1

        elif token.type == Token.IF:
            # Collect the if/elif/else/endif block
            end_idx, branches, else_body = _collect_if_block(tokens, i)
            # Evaluate branches
            rendered = False
            for condition, body_tokens in branches:
                if _eval_condition(condition, context):
                    output.append(_render_tokens(body_tokens, context))
                    rendered = True
                    break
            if not rendered and else_body:
                output.append(_render_tokens(else_body, context))
            i = end_idx + 1

        elif token.type == Token.FOR:
            # Collect the for/endfor block
            end_idx, body_tokens = _collect_for_block(tokens, i)
            var_name, iter_expr = token.value.split("|", 1)
            iterable = _resolve_dotted(iter_expr.strip(), context)

            if iterable and hasattr(iterable, "__iter__"):
                for item in iterable:
                    new_context = dict(context)
                    new_context[var_name.strip()] = item
                    output.append(_render_tokens(body_tokens, new_context))
            i = end_idx + 1

        else:
            raise TemplateSyntaxError(f"Unexpected token {token.type}: {token.value}")

    return "".join(output)


def _collect_if_block(tokens: list, start: int) -> tuple:
    """Collect tokens for an if/elif/else/endif block.

    Returns (end_index, branches, else_body).
    branches is a list of (condition, body_tokens) tuples.
    else_body is a list of tokens or empty list.
    """
    branches = []
    else_body = []
    current_condition = tokens[start].value
    current_body = []
    depth = 0
    i = start + 1

    while i < len(tokens):
        token = tokens[i]

        if token.type == Token.IF:
            depth += 1
            current_body.append(token)
        elif token.type == Token.FOR:
            depth += 1
            current_body.append(token)
        elif token.type == Token.ENDIF:
            if depth > 0:
                depth -= 1
                current_body.append(token)
            else:
                branches.append((current_condition, current_body))
                return i, branches, else_body
        elif token.type == Token.ELIF and depth == 0:
            branches.append((current_condition, current_body))
            current_condition = token.value
            current_body = []
        elif token.type == Token.ELSE and depth == 0:
            branches.append((current_condition, current_body))
            else_body = []
            # Collect else body until endif
            i += 1
            while i < len(tokens):
                if tokens[i].type == Token.ENDIF:
                    return i, branches, else_body
                if tokens[i].type == Token.IF:
                    depth += 1
                elif tokens[i].type == Token.ENDIF:
                    depth -= 1
                else_body.append(tokens[i])
                i += 1
            raise TemplateSyntaxError("Unclosed {% if %} block (missing {% endif %})")
        elif token.type == Token.ENDFOR:
            if depth > 0:
                depth -= 1
                current_body.append(token)
            else:
                current_body.append(token)
        else:
            current_body.append(token)
        i += 1

    raise TemplateSyntaxError("Unclosed {% if %} block (missing {% endif %})")


def _collect_for_block(tokens: list, start: int) -> tuple:
    """Collect tokens for a for/endfor block.

    Returns (end_index, body_tokens).
    """
    body = []
    depth = 0
    i = start + 1

    while i < len(tokens):
        token = tokens[i]

        if token.type == Token.FOR:
            depth += 1
            body.append(token)
        elif token.type == Token.IF:
            depth += 1
            body.append(token)
        elif token.type == Token.ENDFOR:
            if depth > 0:
                depth -= 1
                body.append(token)
            else:
                return i, body
        elif token.type == Token.ENDIF:
            if depth > 0:
                depth -= 1
                body.append(token)
            else:
                raise TemplateSyntaxError("Unexpected {% endif %} without matching {% if %}")
        else:
            body.append(token)
        i += 1

    raise TemplateSyntaxError("Unclosed {% for %} block (missing {% endfor %})")


if __name__ == "__main__":
    # Test basic variable substitution
    print(render("Hello, {{name}}!", {"name": "World"}))

    # Test filters
    print(render("{{greeting|upper}}", {"greeting": "hello"}))
    print(render("{{word|title}}", {"word": "hello world"}))

    # Test if/else
    tmpl = "{% if show %}Visible{% endif %}"
    print(render(tmpl, {"show": True}))
    print(render(tmpl, {"show": False}))

    tmpl2 = "{% if show %}Yes{% else %}No{% endif %}"
    print(render(tmpl2, {"show": False}))

    # Test for loop
    tmpl3 = "{% for item in items %}{{item}}, {% endfor %}"
    print(render(tmpl3, {"items": ["a", "b", "c"]}))

    # Test nested
    tmpl4 = "{% for item in items %}{% if item %}{{item|upper}} {% endif %}{% endfor %}"
    print(render(tmpl4, {"items": ["a", "", "c"]}))

    # Test cycle detection (syntax error)
    try:
        render("{% if x %}test", {"x": True})
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")
