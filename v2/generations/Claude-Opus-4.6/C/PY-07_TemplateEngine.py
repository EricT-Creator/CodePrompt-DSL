import re
from typing import Any, Dict, List, Optional


class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""
    pass


class TemplateEngine:
    VARIABLE_RE = re.compile(r"\{\{(.+?)\}\}")
    BLOCK_RE = re.compile(
        r"\{%\s*(if|elif|else|endif|for|endfor)\s*(.*?)\s*%\}"
    )
    FILTER_SEP = "|"

    BUILTIN_FILTERS = {
        "upper": lambda v: str(v).upper(),
        "lower": lambda v: str(v).lower(),
        "title": lambda v: str(v).title(),
        "strip": lambda v: str(v).strip(),
        "length": lambda v: len(v) if hasattr(v, "__len__") else 0,
        "default": lambda v, d="": d if not v else v,
        "capitalize": lambda v: str(v).capitalize(),
    }

    def __init__(self):
        self.custom_filters: Dict[str, Any] = {}

    def add_filter(self, name: str, func):
        self.custom_filters[name] = func

    def _get_filter(self, name: str):
        if name in self.custom_filters:
            return self.custom_filters[name]
        if name in self.BUILTIN_FILTERS:
            return self.BUILTIN_FILTERS[name]
        raise TemplateSyntaxError(f"Unknown filter: '{name}'")

    def _apply_filters(self, value: Any, filter_chain: str) -> Any:
        filters = [f.strip() for f in filter_chain.split(self.FILTER_SEP) if f.strip()]
        result = value
        for f in filters:
            func = self._get_filter(f)
            result = func(result)
        return result

    def _resolve_variable(self, expr: str, context: Dict[str, Any]) -> Any:
        parts = expr.strip().split(self.FILTER_SEP)
        var_path = parts[0].strip()
        filter_chain = self.FILTER_SEP.join(parts[1:]) if len(parts) > 1 else ""

        value = self._lookup(var_path, context)

        if filter_chain:
            value = self._apply_filters(value, filter_chain)

        return value

    def _lookup(self, path: str, context: Dict[str, Any]) -> Any:
        keys = path.split(".")
        current = context
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return ""
        return current

    def _evaluate_condition(self, expr: str, context: Dict[str, Any]) -> bool:
        expr = expr.strip()

        if " not in " in expr:
            left, right = expr.split(" not in ", 1)
            left_val = self._lookup(left.strip(), context)
            right_val = self._lookup(right.strip(), context)
            return left_val not in right_val
        if " in " in expr:
            left, right = expr.split(" in ", 1)
            left_val = self._lookup(left.strip(), context)
            right_val = self._lookup(right.strip(), context)
            return left_val in right_val

        comparisons = [
            ("==", lambda a, b: a == b),
            ("!=", lambda a, b: a != b),
            (">=", lambda a, b: a >= b),
            ("<=", lambda a, b: a <= b),
            (">", lambda a, b: a > b),
            ("<", lambda a, b: a < b),
        ]
        for op, func in comparisons:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self._resolve_value(left.strip(), context)
                right_val = self._resolve_value(right.strip(), context)
                return func(left_val, right_val)

        if expr.startswith("not "):
            return not self._evaluate_condition(expr[4:], context)

        value = self._resolve_value(expr, context)
        return bool(value)

    def _resolve_value(self, token: str, context: Dict[str, Any]) -> Any:
        if token.startswith(("'", '"')) and token.endswith(("'", '"')):
            return token[1:-1]
        if token == "True":
            return True
        if token == "False":
            return False
        if token == "None":
            return None
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return self._lookup(token, context)

    def _tokenize(self, template: str) -> List[dict]:
        tokens: List[dict] = []
        pos = 0

        combined = re.compile(
            r"(\{\{.+?\}\}|\{%\s*(?:if|elif|else|endif|for|endfor)\s*.*?\s*%\})"
        )

        for match in combined.finditer(template):
            start, end = match.span()
            if start > pos:
                tokens.append({"type": "text", "value": template[pos:start]})

            tag = match.group()
            if tag.startswith("{{"):
                tokens.append({"type": "variable", "value": tag[2:-2].strip()})
            else:
                inner = re.match(r"\{%\s*(\w+)\s*(.*?)\s*%\}", tag)
                if inner:
                    tokens.append({
                        "type": "block",
                        "keyword": inner.group(1),
                        "expr": inner.group(2),
                    })

            pos = end

        if pos < len(template):
            tokens.append({"type": "text", "value": template[pos:]})

        return tokens

    def _parse(self, tokens: List[dict]) -> List[dict]:
        nodes: List[dict] = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token["type"] == "text":
                nodes.append({"type": "text", "value": token["value"]})
                i += 1

            elif token["type"] == "variable":
                nodes.append({"type": "variable", "expr": token["value"]})
                i += 1

            elif token["type"] == "block":
                keyword = token["keyword"]

                if keyword == "if":
                    node, consumed = self._parse_if(tokens, i)
                    nodes.append(node)
                    i += consumed

                elif keyword == "for":
                    node, consumed = self._parse_for(tokens, i)
                    nodes.append(node)
                    i += consumed

                elif keyword in ("endif", "endfor", "else", "elif"):
                    break

                else:
                    i += 1
            else:
                i += 1

        return nodes

    def _parse_if(self, tokens: List[dict], start: int) -> tuple:
        branches: List[dict] = []
        current_expr = tokens[start]["expr"]
        current_body_tokens: List[dict] = []
        i = start + 1
        depth = 0

        while i < len(tokens):
            token = tokens[i]

            if token["type"] == "block":
                kw = token["keyword"]

                if kw == "if":
                    depth += 1
                    current_body_tokens.append(token)
                    i += 1
                elif kw == "endif" and depth > 0:
                    depth -= 1
                    current_body_tokens.append(token)
                    i += 1
                elif kw == "endif" and depth == 0:
                    branches.append({
                        "condition": current_expr,
                        "body": self._parse(current_body_tokens),
                    })
                    i += 1
                    break
                elif kw == "elif" and depth == 0:
                    branches.append({
                        "condition": current_expr,
                        "body": self._parse(current_body_tokens),
                    })
                    current_expr = token["expr"]
                    current_body_tokens = []
                    i += 1
                elif kw == "else" and depth == 0:
                    branches.append({
                        "condition": current_expr,
                        "body": self._parse(current_body_tokens),
                    })
                    current_expr = None
                    current_body_tokens = []
                    i += 1
                else:
                    current_body_tokens.append(token)
                    i += 1
            else:
                current_body_tokens.append(token)
                i += 1
        else:
            raise TemplateSyntaxError("Missing {% endif %}")

        return {"type": "if", "branches": branches}, i - start

    def _parse_for(self, tokens: List[dict], start: int) -> tuple:
        expr = tokens[start]["expr"]
        match = re.match(r"(\w+)\s+in\s+(.+)", expr)
        if not match:
            raise TemplateSyntaxError(f"Invalid for syntax: {expr}")

        loop_var = match.group(1)
        iterable_expr = match.group(2).strip()

        body_tokens: List[dict] = []
        i = start + 1
        depth = 0

        while i < len(tokens):
            token = tokens[i]
            if token["type"] == "block":
                kw = token["keyword"]
                if kw == "for":
                    depth += 1
                    body_tokens.append(token)
                elif kw == "endfor" and depth > 0:
                    depth -= 1
                    body_tokens.append(token)
                elif kw == "endfor" and depth == 0:
                    i += 1
                    break
                else:
                    body_tokens.append(token)
            else:
                body_tokens.append(token)
            i += 1
        else:
            raise TemplateSyntaxError("Missing {% endfor %}")

        body = self._parse(body_tokens)

        return {
            "type": "for",
            "loop_var": loop_var,
            "iterable": iterable_expr,
            "body": body,
        }, i - start

    def _render_nodes(self, nodes: List[dict], context: Dict[str, Any]) -> str:
        output: List[str] = []

        for node in nodes:
            ntype = node["type"]

            if ntype == "text":
                output.append(node["value"])

            elif ntype == "variable":
                value = self._resolve_variable(node["expr"], context)
                output.append(str(value))

            elif ntype == "if":
                for branch in node["branches"]:
                    if branch["condition"] is None or self._evaluate_condition(
                        branch["condition"], context
                    ):
                        output.append(self._render_nodes(branch["body"], context))
                        break

            elif ntype == "for":
                iterable = self._lookup(node["iterable"], context)
                if not hasattr(iterable, "__iter__"):
                    raise TemplateSyntaxError(
                        f"'{node['iterable']}' is not iterable"
                    )
                for item in iterable:
                    child_ctx = {**context, node["loop_var"]: item}
                    output.append(self._render_nodes(node["body"], child_ctx))

        return "".join(output)

    def render(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        if context is None:
            context = {}
        tokens = self._tokenize(template)
        ast = self._parse(tokens)
        return self._render_nodes(ast, context)


def render(template: str, context: Optional[Dict[str, Any]] = None) -> str:
    engine = TemplateEngine()
    return engine.render(template, context or {})


if __name__ == "__main__":
    engine = TemplateEngine()

    # Basic variable substitution
    print("=== Variables ===")
    print(engine.render("Hello, {{ name }}!", {"name": "World"}))

    # Filters
    print("\n=== Filters ===")
    print(engine.render("{{ name|upper }}", {"name": "alice"}))
    print(engine.render("{{ name|lower }}", {"name": "BOB"}))
    print(engine.render("{{ name|title }}", {"name": "hello world"}))

    # If/elif/else
    print("\n=== Conditionals ===")
    tmpl = "{% if is_admin %}Admin{% elif is_mod %}Moderator{% else %}User{% endif %}"
    print(engine.render(tmpl, {"is_admin": False, "is_mod": True}))
    print(engine.render(tmpl, {"is_admin": True, "is_mod": False}))
    print(engine.render(tmpl, {"is_admin": False, "is_mod": False}))

    # For loops
    print("\n=== Loops ===")
    print(engine.render(
        "{% for item in items %}* {{ item }}\n{% endfor %}",
        {"items": ["apple", "banana", "cherry"]},
    ))

    # Nested blocks
    print("=== Nested ===")
    nested = """{% for user in users %}{{ user.name }}:{% if user.active %} active{% else %} inactive{% endif %}
{% endfor %}"""
    print(engine.render(nested, {
        "users": [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Carol", "active": True},
        ]
    }))

    # Error handling
    print("=== Error Test ===")
    try:
        engine.render("{% if x %}oops")
    except TemplateSyntaxError as e:
        print(f"Caught: {e}")
