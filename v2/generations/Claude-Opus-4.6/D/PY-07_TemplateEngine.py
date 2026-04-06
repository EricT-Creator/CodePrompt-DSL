import re
from typing import Any, Dict, List, Optional


class TemplateSyntaxError(Exception):
    """Raised when the template contains syntax errors."""
    pass


FILTER_MAP = {
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "title": lambda v: str(v).title(),
}


def _apply_filters(value: Any, filters: List[str]) -> str:
    result = value
    for f in filters:
        f = f.strip()
        if f in FILTER_MAP:
            result = FILTER_MAP[f](result)
        else:
            raise TemplateSyntaxError(f"Unknown filter: '{f}'")
    return str(result)


def _resolve_variable(name: str, context: Dict[str, Any]) -> Any:
    parts = name.split(".")
    value = context
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return ""
    return value


def _substitute_variables(text: str, context: Dict[str, Any]) -> str:
    pattern = re.compile(r"\{\{\s*(.+?)\s*\}\}")

    def replacer(match: re.Match) -> str:
        expr = match.group(1).strip()
        parts = expr.split("|")
        var_name = parts[0].strip()
        filters = parts[1:] if len(parts) > 1 else []
        value = _resolve_variable(var_name, context)
        if filters:
            return _apply_filters(value, filters)
        return str(value)

    return pattern.sub(replacer, text)


def _find_matching_end(tokens: List[str], start: int, open_tag: str, close_tag: str) -> int:
    depth = 1
    i = start
    while i < len(tokens):
        token = tokens[i].strip()
        if re.match(r"\{%\s*" + open_tag + r"\b", token):
            depth += 1
        elif re.match(r"\{%\s*" + close_tag + r"\s*%\}", token):
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise TemplateSyntaxError(f"Missing {{% {close_tag} %}} for {{% {open_tag} %}}")


def _tokenize(template: str) -> List[str]:
    pattern = re.compile(r"(\{%.*?%\})")
    tokens = pattern.split(template)
    return tokens


def _process_tokens(tokens: List[str], context: Dict[str, Any]) -> str:
    output = []
    i = 0

    while i < len(tokens):
        token = tokens[i]
        stripped = token.strip()

        for_match = re.match(
            r"\{%\s*for\s+(\w+)\s+in\s+(\w+(?:\.\w+)*)\s*%\}", stripped
        )
        if for_match:
            var_name = for_match.group(1)
            iterable_name = for_match.group(2)

            end_idx = _find_matching_end(tokens, i + 1, "for", "endfor")
            body_tokens = tokens[i + 1 : end_idx]

            iterable = _resolve_variable(iterable_name, context)
            if not hasattr(iterable, "__iter__"):
                raise TemplateSyntaxError(
                    f"'{iterable_name}' is not iterable"
                )

            for item in iterable:
                loop_context = {**context, var_name: item}
                output.append(_process_tokens(body_tokens, loop_context))

            i = end_idx + 1
            continue

        if_match = re.match(
            r"\{%\s*if\s+(.+?)\s*%\}", stripped
        )
        if if_match:
            condition_expr = if_match.group(1).strip()

            end_idx = _find_matching_end(tokens, i + 1, "if", "endif")
            body_tokens = tokens[i + 1 : end_idx]

            else_idx: Optional[int] = None
            depth = 0
            for j in range(len(body_tokens)):
                bt = body_tokens[j].strip()
                if re.match(r"\{%\s*if\b", bt):
                    depth += 1
                elif re.match(r"\{%\s*endif\s*%\}", bt):
                    depth -= 1
                elif depth == 0 and re.match(r"\{%\s*else\s*%\}", bt):
                    else_idx = j
                    break

            condition_value = _evaluate_condition(condition_expr, context)

            if condition_value:
                if else_idx is not None:
                    true_tokens = body_tokens[:else_idx]
                else:
                    true_tokens = body_tokens
                output.append(_process_tokens(true_tokens, context))
            else:
                if else_idx is not None:
                    false_tokens = body_tokens[else_idx + 1 :]
                    output.append(_process_tokens(false_tokens, context))

            i = end_idx + 1
            continue

        if re.match(r"\{%\s*(endfor|endif|else)\s*%\}", stripped):
            raise TemplateSyntaxError(f"Unexpected tag: {stripped}")

        if re.match(r"\{%.*%\}", stripped):
            raise TemplateSyntaxError(f"Unknown block tag: {stripped}")

        output.append(_substitute_variables(token, context))
        i += 1

    return "".join(output)


def _evaluate_condition(expr: str, context: Dict[str, Any]) -> bool:
    not_match = re.match(r"^not\s+(.+)$", expr.strip())
    if not_match:
        inner = not_match.group(1).strip()
        return not _evaluate_condition(inner, context)

    and_parts = re.split(r"\s+and\s+", expr)
    if len(and_parts) > 1:
        return all(_evaluate_condition(p.strip(), context) for p in and_parts)

    or_parts = re.split(r"\s+or\s+", expr)
    if len(or_parts) > 1:
        return any(_evaluate_condition(p.strip(), context) for p in or_parts)

    comp_match = re.match(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$", expr)
    if comp_match:
        left = _resolve_value(comp_match.group(1).strip(), context)
        op = comp_match.group(2)
        right = _resolve_value(comp_match.group(3).strip(), context)
        if op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        elif op == "<=":
            return left <= right

    value = _resolve_variable(expr.strip(), context)
    return bool(value)


def _resolve_value(token: str, context: Dict[str, Any]) -> Any:
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        return token[1:-1]
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    if token == "True":
        return True
    if token == "False":
        return False
    if token == "None":
        return None
    return _resolve_variable(token, context)


def render(template: str, context: Dict[str, Any]) -> str:
    unclosed_blocks = re.findall(r"\{%\s*(for|if)\b", template)
    end_blocks_for = len(re.findall(r"\{%\s*endfor\s*%\}", template))
    end_blocks_if = len(re.findall(r"\{%\s*endif\s*%\}", template))
    for_blocks = len(re.findall(r"\{%\s*for\b", template))
    if_blocks = len(re.findall(r"\{%\s*if\b", template))

    if for_blocks != end_blocks_for:
        raise TemplateSyntaxError(
            f"Mismatched for/endfor: {for_blocks} for vs {end_blocks_for} endfor"
        )
    if if_blocks != end_blocks_if:
        raise TemplateSyntaxError(
            f"Mismatched if/endif: {if_blocks} if vs {end_blocks_if} endif"
        )

    tokens = _tokenize(template)
    return _process_tokens(tokens, context)


if __name__ == "__main__":
    print("=== Variable Substitution ===")
    print(render("Hello, {{ name }}!", {"name": "World"}))
    print(render("{{ greeting|upper }}, {{ name|title }}!", {"greeting": "hello", "name": "alice"}))

    print("\n=== Conditionals ===")
    tpl_if = "{% if show %}Visible{% endif %}"
    print(render(tpl_if, {"show": True}))
    print(render(tpl_if, {"show": False}))

    tpl_else = "{% if admin %}Admin{% else %}Guest{% endif %}"
    print(render(tpl_else, {"admin": True}))
    print(render(tpl_else, {"admin": False}))

    print("\n=== Loops ===")
    tpl_loop = "Items: {% for item in items %}[{{ item }}] {% endfor %}"
    print(render(tpl_loop, {"items": ["a", "b", "c"]}))

    print("\n=== Nested ===")
    tpl_nested = """{% for user in users %}{{ user.name }}: {% if user.active %}Active{% else %}Inactive{% endif %}
{% endfor %}"""
    ctx = {
        "users": [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Carol", "active": True},
        ]
    }
    print(render(tpl_nested, ctx))

    print("=== Filters ===")
    print(render("{{ msg|upper }}", {"msg": "hello world"}))
    print(render("{{ msg|lower }}", {"msg": "HELLO WORLD"}))
    print(render("{{ msg|title }}", {"msg": "hello world"}))

    print("\n=== Syntax Error ===")
    try:
        render("{% for x in items %}no end", {"items": [1]})
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")
