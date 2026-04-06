"""
简易模板引擎 - 变量替换/条件/循环/过滤器
不使用jinja2/mako，用正则解析
"""


import re


class TemplateSyntaxError(Exception):
    pass


class TemplateEngine:
    def __init__(self):
        self._var_re = re.compile(r'\{\{\s*(\w+(?:\.\w+)*)\s*\}\}')
        self._filter_re = re.compile(r'(\w+(?:\.\w+)*)(\|[a-zA-Z_]+)*')

    def _apply_filters(self, value: object, filter_str: str) -> str:
        if not filter_str:
            return str(value)

        filters = [f.strip() for f in filter_str.split("|") if f.strip()]
        result = str(value)

        for f in filters:
            if f == "upper":
                result = result.upper()
            elif f == "lower":
                result = result.lower()
            elif f == "title":
                result = result.title()
            elif f == "strip":
                result = result.strip()
            elif f == "length":
                return str(len(result))
            elif f == "reverse":
                result = result[::-1]
            else:
                raise TemplateSyntaxError(f"未知过滤器: {f}")

        return result

    def _resolve_var(self, name: str, context: dict) -> object:
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

    def _process_text(self, text: str, context: dict) -> str:
        def replace_var(match):
            expr = match.group(1)
            parts = expr.split("|")
            var_name = parts[0].strip()
            filter_str = "|".join(parts[1:])
            value = self._resolve_var(var_name, context)
            return self._apply_filters(value, filter_str)

        return self._var_re.sub(replace_var, text)

    def _find_matching(self, tokens: list, start: int, open_tag: str, close_tag: str) -> int:
        depth = 0
        for i in range(start, len(tokens)):
            if tokens[i]["type"] == "tag" and tokens[i]["content"] == open_tag:
                depth += 1
            elif tokens[i]["type"] == "tag" and tokens[i]["content"] == close_tag:
                depth -= 1
                if depth == 0:
                    return i
        raise TemplateSyntaxError(f"未找到匹配的 {close_tag}")

    def _tokenize(self, template: str) -> list:
        tokens = []
        pattern = re.compile(r'(\{%.*?%\}|\{\{.*?\}\})', re.DOTALL)
        parts = pattern.split(template)

        for part in parts:
            if not part:
                continue
            if part.startswith("{%") and part.endswith("%}"):
                content = part[2:-2].strip()
                tokens.append({"type": "tag", "content": content})
            elif part.startswith("{{") and part.endswith("}}"):
                content = part[2:-2].strip()
                tokens.append({"type": "var", "content": content})
            else:
                tokens.append({"type": "text", "content": part})

        return tokens

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        condition = condition.strip()

        neg_match = re.match(r'^not\s+(.+)$', condition)
        if neg_match:
            return not self._evaluate_condition(neg_match.group(1), context)

        op_match = re.match(r'^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$', condition)
        if op_match:
            left = self._resolve_var(op_match.group(1).strip(), context)
            op = op_match.group(2)
            right = self._resolve_var(op_match.group(3).strip(), context)
            try:
                left_val = int(left) if str(left).isdigit() else left
                right_val = int(right) if str(right).isdigit() else right
            except (ValueError, TypeError):
                left_val = str(left)
                right_val = str(right)
            if op == "==": return left_val == right_val
            if op == "!=": return left_val != right_val
            if op == ">": return left_val > right_val
            if op == "<": return left_val < right_val
            if op == ">=": return left_val >= right_val
            if op == "<=": return left_val <= right_val

        value = self._resolve_var(condition, context)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return value is not None

    def _render_tokens(self, tokens: list, context: dict) -> str:
        result = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token["type"] == "text":
                result.append(token["content"])
                i += 1

            elif token["type"] == "var":
                parts = token["content"].split("|")
                var_name = parts[0].strip()
                filter_str = "|".join(parts[1:])
                value = self._resolve_var(var_name, context)
                result.append(self._apply_filters(value, filter_str))
                i += 1

            elif token["type"] == "tag":
                content = token["content"]

                if content.startswith("if "):
                    condition = content[3:]
                    else_pos = self._find_matching(tokens, i + 1, "else", "endif")
                    endif_pos = self._find_matching(tokens, i + 1, "else", "endif")
                    if else_pos < endif_pos:
                        true_tokens = tokens[i + 1:else_pos]
                        false_tokens = tokens[else_pos + 1:endif_pos]
                    else:
                        true_tokens = tokens[i + 1:endif_pos]
                        false_tokens = []

                    if self._evaluate_condition(condition, context):
                        result.append(self._render_tokens(true_tokens, context))
                    else:
                        result.append(self._render_tokens(false_tokens, context))
                    i = endif_pos + 1

                elif content.startswith("for "):
                    for_match = re.match(r'for\s+(\w+)\s+in\s+(.+)', content)
                    if not for_match:
                        raise TemplateSyntaxError(f"无效的for语法: {content}")
                    var_name = for_match.group(1)
                    iterable_name = for_match.group(2).strip()
                    endfor_pos = self._find_matching(tokens, i + 1, "for", "endfor")
                    body_tokens = tokens[i + 1:endfor_pos]

                    iterable = self._resolve_var(iterable_name, context)
                    if not isinstance(iterable, (list, tuple)):
                        iterable = list(iterable) if iterable else []

                    for item in iterable:
                        child_context = {**context, var_name: item}
                        result.append(self._render_tokens(body_tokens, child_context))

                    i = endfor_pos + 1

                elif content == "else":
                    raise TemplateSyntaxError("else 出现在 if 块外部")

                elif content in ("endif", "endfor"):
                    raise TemplateSyntaxError(f"{content} 出现在块外部")

                else:
                    raise TemplateSyntaxError(f"未知标签: {content}")

            else:
                i += 1

        return "".join(result)

    def render(self, template: str, context: dict) -> str:
        tokens = self._tokenize(template)
        return self._render_tokens(tokens, context)


def main():
    engine = TemplateEngine()

    template = """
<h1>{{ title|upper }}</h1>
<p>作者: {{ author|title }}</p>

{% if show_list %}
<ul>
{% for item in items %}
  <li>{{ item.name }} - {{ item.price|title }}</li>
{% endfor %}
</ul>
{% endif %}

{% if count > 3 %}
<p>共 {{ count }} 个项目</p>
{% else %}
<p>项目不足</p>
{% endif %}
"""

    context = {
        "title": "商品列表",
        "author": "alice smith",
        "show_list": True,
        "count": 5,
        "items": [
            {"name": "苹果", "price": "5.00元"},
            {"name": "香蕉", "price": "3.50元"},
            {"name": "橙子", "price": "4.20元"},
        ],
    }

    result = engine.render(template, context)
    print(result.strip())
    return result


if __name__ == "__main__":
    main()
