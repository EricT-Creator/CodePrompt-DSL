import re
from typing import Any, Dict, Optional


class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        super().__init__(f"Syntax error at line {line}, col {col}: {message}" if line else message)


class TemplateEngine:
    FILTERS: Dict[str, callable] = {
        "upper": lambda v: str(v).upper(),
        "lower": lambda v: str(v).lower(),
        "title": lambda v: str(v).title(),
        "strip": lambda v: str(v).strip(),
        "length": lambda v: len(v) if hasattr(v, "__len__") else 0,
        "default": lambda v, d="": v if v else d,
        "join": lambda v, sep=", ": sep.join(str(i) for i in v) if hasattr(v, "__iter__") and not isinstance(v, str) else str(v),
        "first": lambda v: next(iter(v)) if hasattr(v, "__iter__") and not isinstance(v, str) else v,
        "last": lambda v: list(v)[-1] if hasattr(v, "__iter__") and not isinstance(v, str) else v,
    }

    def __init__(self):
        self._re_var = re.compile(r'\{\{\s*([\w.]+)((?:\s*\|\s*\w+(?:\s*:\s*"[^"]*")?)*)\s*\}\}')
        self._re_block = re.compile(r'\{%\s*(\w+)(.*?)\s*%\}')
        self._re_end_block = re.compile(r'\{%\s*end(\w+)\s*%\}')

    def apply_filter(self, value: Any, filter_chain: str) -> Any:
        if not filter_chain:
            return value
        filters = [f.strip() for f in filter_chain.split("|") if f.strip()]
        result = value
        for f in filters:
            parts = f.split(":", 1)
            name = parts[0].strip()
            args_str = parts[1].strip() if len(parts) > 1 else ""
            args = []
            if args_str:
                arg_match = re.findall(r'"([^"]*)"', args_str)
                args.extend(arg_match)
            if name not in self.FILTERS:
                raise TemplateSyntaxError(f"Unknown filter: '{name}'")
            result = self.FILTERS[name](result, *args)
        return result

    def resolve_variable(self, name: str, context: Dict[str, Any]) -> Any:
        parts = name.split(".")
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

    def _find_matching_end(self, tokens: list, start: int, block_type: str) -> int:
        depth = 1
        i = start + 1
        while i < len(tokens):
            token_type, content = tokens[i]
            if token_type == "block":
                directive = content.split()[0] if content.strip() else ""
                if directive == block_type:
                    depth += 1
                elif directive == f"end{block_type}":
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        raise TemplateSyntaxError(f"No matching end{block_type} found")

    def _parse_tokens(self, source: str) -> list:
        tokens = []
        pos = 0
        combined = re.compile(r'(\{%.*?%\}|\{\{.*?\}\})', re.DOTALL)
        parts = combined.split(source)

        for part in parts:
            if part.startswith("{%") and part.endswith("%}"):
                inner = part[2:-2].strip()
                if inner.startswith("end"):
                    tokens.append(("endblock", inner))
                else:
                    tokens.append(("block", inner))
            elif part.startswith("{{") and part.endswith("}}"):
                tokens.append(("var", part[2:-2].strip()))
            else:
                if part:
                    tokens.append(("text", part))
        return tokens

    def render(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        if context is None:
            context = {}
        tokens = self._parse_tokens(template)
        return self._render_tokens(tokens, context)

    def _render_tokens(self, tokens: list, context: Dict[str, Any]) -> str:
        output = []
        i = 0
        while i < len(tokens):
            token_type, content = tokens[i]

            if token_type == "text":
                output.append(content)
                i += 1

            elif token_type == "var":
                match = self._re_var.match("{{ " + content + " }}")
                if match:
                    var_name = match.group(1)
                    filter_chain = match.group(2) or ""
                    value = self.resolve_variable(var_name, context)
                    value = self.apply_filter(value, filter_chain)
                    output.append(str(value))
                else:
                    output.append(f"{{{{ {content} }}}}")
                i += 1

            elif token_type == "block":
                parts = content.split(None, 1)
                directive = parts[0] if parts else ""
                args = parts[1].strip() if len(parts) > 1 else ""

                if directive == "if":
                    end_idx = self._find_matching_end(tokens, i, "if")
                    body_tokens = tokens[i + 1 : end_idx]
                    cond_result = self._eval_condition(args, context)
                    if cond_result:
                        output.append(self._render_tokens(body_tokens, context))
                    i = end_idx + 1

                elif directive == "for":
                    end_idx = self._find_matching_end(tokens, i, "for")
                    body_tokens = tokens[i + 1 : end_idx]
                    for_match = re.match(r'(\w+)\s+in\s+(.+)', args)
                    if not for_match:
                        raise TemplateSyntaxError(f"Invalid for syntax: '{args}'")
                    var_name = for_match.group(1)
                    iterable_name = for_match.group(2).strip()
                    iterable = self.resolve_variable(iterable_name, context)
                    if iterable and hasattr(iterable, "__iter__"):
                        for item in iterable:
                            new_context = {**context, var_name: item, "loop": {
                                "index": len(output),
                                "first": iterable.index(item) == 0 if isinstance(iterable, list) else False,
                                "last": iterable.index(item) == len(list(iterable)) - 1 if isinstance(iterable, list) else False,
                            }}
                            output.append(self._render_tokens(body_tokens, new_context))
                    i = end_idx + 1

                else:
                    raise TemplateSyntaxError(f"Unknown block directive: '{directive}'")
            else:
                i += 1

        return "".join(output)

    def _eval_condition(self, expr: str, context: Dict[str, Any]) -> bool:
        expr = expr.strip()
        operators = [" and ", " or ", " not "]
        if " and " in expr:
            parts = expr.split(" and ")
            return all(self._eval_condition(p.strip(), context) for p in parts)
        if " or " in expr:
            parts = expr.split(" or ")
            return any(self._eval_condition(p.strip(), context) for p in parts)
        if expr.startswith("not "):
            return not self._eval_condition(expr[4:].strip(), context)

        for op in ["==", "!=", ">=", "<=", ">", "<"]:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self._resolve_value(left.strip(), context)
                right_val = self._resolve_value(right.strip(), context)
                if op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val
                elif op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val

        val = self._resolve_value(expr, context)
        return bool(val)

    def _resolve_value(self, token: str, context: Dict[str, Any]) -> Any:
        token = token.strip()
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            return token[1:-1]
        if token in ("True", "true"):
            return True
        if token in ("False", "false"):
            return False
        if token in ("None", "none"):
            return None
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return self.resolve_variable(token, context)


def demo():
    engine = TemplateEngine()
    context = {
        "name": "World",
        "items": ["Apple", "Banana", "Cherry"],
        "user": {"name": "Alice", "role": "admin"},
        "show_greeting": True,
        "count": 42,
        "empty_list": [],
    }

    template = """Hello, {{ name|upper }}!
{% if show_greeting %}
Welcome back, {{ user.name }}!
Your role is: {{ user.role|title }}.
{% endif %}
{% if count > 10 %}
You have {{ count }} items.
{% endif %}
{% for item in items %}
- {{ item|lower }}
{% endfor %}
{% if not empty_list %}
The list is empty.
{% endif %}
Items: {{ items|join:", " }}"""

    print("=== Template Rendering Demo ===")
    result = engine.render(template, context)
    print(result)

    print("\n=== Error Handling ===")
    try:
        engine.render("{% if %}", context)
    except TemplateSyntaxError as e:
        print(f"Caught error: {e}")

    try:
        engine.render("{% if x %}unclosed", context)
    except TemplateSyntaxError as e:
        print(f"Caught error: {e}")


if __name__ == "__main__":
    demo()
