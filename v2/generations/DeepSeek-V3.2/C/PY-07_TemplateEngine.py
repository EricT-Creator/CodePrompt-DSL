import re
from dataclasses import dataclass
from typing import Dict, Any, List, Union, Callable
from datetime import datetime

@dataclass
class TemplateSyntaxError(Exception):
    """自定义模板语法错误"""
    message: str
    line: int
    column: int
    
    def __str__(self):
        return f"TemplateSyntaxError at line {self.line}, column {self.column}: {self.message}"

class TemplateEngine:
    """简易模板引擎"""
    
    def __init__(self):
        self.filters: Dict[str, Callable] = {
            'upper': str.upper,
            'lower': str.lower,
            'title': str.title,
            'capitalize': str.capitalize,
            'strip': str.strip,
            'length': len,
            'datetime': lambda x: datetime.now().strftime(x) if x else datetime.now().isoformat(),
            'default': lambda val, default: val if val else default,
        }
        
    def register_filter(self, name: str, func: Callable):
        """注册自定义过滤器"""
        self.filters[name] = func
    
    def _parse_tokens(self, template: str) -> List[Dict]:
        """解析模板为token序列"""
        tokens = []
        pos = 0
        line = 1
        column = 1
        
        # 正则表达式匹配模板语法
        patterns = [
            (r'\{\{\s*(.*?)\s*\}\}', 'variable'),  # {{ var }}
            (r'\{%\s*if\s+(.*?)\s*%\}', 'if_start'),  # {% if cond %}
            (r'\{%\s*elif\s+(.*?)\s*%\}', 'elif'),     # {% elif cond %}
            (r'\{%\s*else\s*%\}', 'else'),             # {% else %}
            (r'\{%\s*endif\s*%\}', 'if_end'),          # {% endif %}
            (r'\{%\s*for\s+(.*?)\s+in\s+(.*?)\s*%\}', 'for_start'),  # {% for x in list %}
            (r'\{%\s*endfor\s*%\}', 'for_end'),        # {% endfor %}
        ]
        
        while pos < len(template):
            matched = False
            
            for pattern, token_type in patterns:
                match = re.match(pattern, template[pos:], re.DOTALL)
                if match:
                    # 添加前面的文本token
                    if pos < match.start() + pos:
                        text = template[pos:match.start() + pos]
                        tokens.append({
                            'type': 'text',
                            'value': text,
                            'line': line,
                            'column': column
                        })
                        # 更新行列计数
                        line_breaks = text.count('\n')
                        if line_breaks:
                            line += line_breaks
                            column = len(text.split('\n')[-1]) + 1
                        else:
                            column += len(text)
                    
                    # 添加语法token
                    groups = match.groups()
                    tokens.append({
                        'type': token_type,
                        'value': groups[0] if groups else None,
                        'groups': groups,
                        'line': line,
                        'column': column
                    })
                    
                    # 更新位置
                    pos += match.end()
                    # 更新列（假设语法token在同一行）
                    column += len(match.group())
                    matched = True
                    break
            
            if not matched:
                # 普通文本
                char = template[pos]
                tokens.append({
                    'type': 'text',
                    'value': char,
                    'line': line,
                    'column': column
                })
                if char == '\n':
                    line += 1
                    column = 1
                else:
                    column += 1
                pos += 1
        
        return tokens
    
    def _apply_filters(self, value: Any, filter_chain: str) -> str:
        """应用过滤器链"""
        if filter_chain:
            filters = [f.strip() for f in filter_chain.split('|')]
            for filter_name in filters:
                if filter_name in self.filters:
                    try:
                        value = self.filters[filter_name](value)
                    except Exception as e:
                        raise TemplateSyntaxError(
                            f"Filter '{filter_name}' error: {str(e)}",
                            line=0, column=0
                        )
                else:
                    raise TemplateSyntaxError(
                        f"Unknown filter: '{filter_name}'",
                        line=0, column=0
                    )
        return str(value) if value is not None else ''
    
    def _evaluate_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """安全地计算表达式"""
        expr = expr.strip()
        
        # 检查过滤器
        if '|' in expr:
            var_part, filter_part = expr.split('|', 1)
            var_name = var_part.strip()
            filter_chain = filter_part.strip()
        else:
            var_name = expr
            filter_chain = ''
        
        # 从上下文中获取变量
        if var_name in context:
            value = context[var_name]
        else:
            # 尝试访问嵌套属性
            parts = var_name.split('.')
            value = context
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    value = None
                    break
        
        # 应用过滤器
        return self._apply_filters(value, filter_chain)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """计算条件表达式"""
        condition = condition.strip()
        
        # 简单条件：检查变量是否为真
        if condition in context:
            value = context[condition]
            return bool(value)
        
        # 比较操作
        operators = ['==', '!=', '>', '<', '>=', '<=', ' in ', ' not in ']
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._evaluate_expression(left.strip(), context)
                right_val = self._evaluate_expression(right.strip(), context)
                
                if op == '==':
                    return str(left_val) == str(right_val)
                elif op == '!=':
                    return str(left_val) != str(right_val)
                elif op == '>':
                    try:
                        return float(left_val) > float(right_val)
                    except ValueError:
                        return str(left_val) > str(right_val)
                elif op == '<':
                    try:
                        return float(left_val) < float(right_val)
                    except ValueError:
                        return str(left_val) < str(right_val)
                elif op == '>=':
                    try:
                        return float(left_val) >= float(right_val)
                    except ValueError:
                        return str(left_val) >= str(right_val)
                elif op == '<=':
                    try:
                        return float(left_val) <= float(right_val)
                    except ValueError:
                        return str(left_val) <= str(right_val)
                elif op == ' in ':
                    return str(left_val) in str(right_val)
                elif op == ' not in ':
                    return str(left_val) not in str(right_val)
        
        # 如果找不到操作符，尝试作为表达式计算
        try:
            result = self._evaluate_expression(condition, context)
            return bool(result)
        except:
            return False
    
    def render(self, template: str, context: Dict[str, Any] = None) -> str:
        """渲染模板"""
        if context is None:
            context = {}
        
        try:
            tokens = self._parse_tokens(template)
        except Exception as e:
            raise TemplateSyntaxError(
                f"Template parsing error: {str(e)}",
                line=1, column=1
            )
        
        output = []
        stack = []  # 用于跟踪if/for块的嵌套
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token['type'] == 'text':
                output.append(token['value'])
                
            elif token['type'] == 'variable':
                expr = token['value']
                try:
                    value = self._evaluate_expression(expr, context)
                    output.append(value)
                except TemplateSyntaxError:
                    raise
                except Exception as e:
                    raise TemplateSyntaxError(
                        f"Error evaluating expression '{expr}': {str(e)}",
                        token['line'], token['column']
                    )
            
            elif token['type'] == 'if_start':
                condition = token['value']
                result = self._evaluate_condition(condition, context)
                stack.append({
                    'type': 'if',
                    'result': result,
                    'matched': result,
                    'skipping': not result
                })
                
            elif token['type'] == 'elif':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateSyntaxError(
                        "{% elif %} without {% if %}",
                        token['line'], token['column']
                    )
                
                condition = token['value']
                if stack[-1]['matched']:
                    stack[-1]['skipping'] = True
                else:
                    result = self._evaluate_condition(condition, context)
                    stack[-1]['skipping'] = not result
                    stack[-1]['matched'] = result
            
            elif token['type'] == 'else':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateSyntaxError(
                        "{% else %} without {% if %}",
                        token['line'], token['column']
                    )
                
                if stack[-1]['matched']:
                    stack[-1]['skipping'] = True
                else:
                    stack[-1]['skipping'] = False
            
            elif token['type'] == 'if_end':
                if not stack or stack[-1]['type'] != 'if':
                    raise TemplateSyntaxError(
                        "{% endif %} without {% if %}",
                        token['line'], token['column']
                    )
                stack.pop()
            
            elif token['type'] == 'for_start':
                if not token['groups'] or len(token['groups']) < 2:
                    raise TemplateSyntaxError(
                        "Invalid {% for %} syntax",
                        token['line'], token['column']
                    )
                
                var_expr = token['groups'][0]  # 如 "user" 或 "key,value"
                iter_expr = token['groups'][1]  # 如 "users"
                
                # 解析迭代变量
                if ',' in var_expr:
                    var_parts = [v.strip() for v in var_expr.split(',')]
                    if len(var_parts) != 2:
                        raise TemplateSyntaxError(
                            "{% for %} expects 'item' or 'key,value'",
                            token['line'], token['column']
                        )
                    var_name = var_parts[0]
                    value_name = var_parts[1]
                else:
                    var_name = var_expr
                    value_name = None
                
                # 获取迭代对象
                try:
                    iterable = self._evaluate_expression(iter_expr, context)
                except Exception as e:
                    raise TemplateSyntaxError(
                        f"Error evaluating for loop iterable: {str(e)}",
                        token['line'], token['column']
                    )
                
                if not hasattr(iterable, '__iter__'):
                    raise TemplateSyntaxError(
                        f"'{iter_expr}' is not iterable",
                        token['line'], token['column']
                    )
                
                # 开始循环
                stack.append({
                    'type': 'for',
                    'var_name': var_name,
                    'value_name': value_name,
                    'iterable': list(iterable) if not isinstance(iterable, dict) else list(iterable.items()),
                    'index': 0,
                    'skipping': False  # for循环不跳过
                })
            
            elif token['type'] == 'for_end':
                if not stack or stack[-1]['type'] != 'for':
                    raise TemplateSyntaxError(
                        "{% endfor %} without {% for %}",
                        token['line'], token['column']
                    )
                
                for_info = stack[-1]
                for_info['index'] += 1
                
                if for_info['index'] < len(for_info['iterable']):
                    # 继续下一次迭代
                    i = for_info['loop_start'] - 1  # 回到for开始位置
                else:
                    # 循环结束
                    stack.pop()
            
            # 检查是否跳过当前内容
            skipping = any(item.get('skipping', False) for item in stack)
            if skipping and token['type'] not in ['if_start', 'elif', 'else', 'if_end', 'for_start', 'for_end']:
                # 跳过输出内容
                pass
            
            # 记录for循环的开始位置
            if token['type'] == 'for_start':
                stack[-1]['loop_start'] = i + 1
            
            i += 1
        
        # 检查未闭合的块
        if stack:
            last_token = stack[-1]
            if last_token['type'] == 'if':
                raise TemplateSyntaxError(
                    "Unclosed {% if %} block",
                    line=1, column=1
                )
            elif last_token['type'] == 'for':
                raise TemplateSyntaxError(
                    "Unclosed {% for %} block",
                    line=1, column=1
                )
        
        return ''.join(output)


# 使用示例
if __name__ == "__main__":
    engine = TemplateEngine()
    
    # 示例1：基本变量和过滤器
    template1 = """
Hello {{ name | upper }}!

Today is {{ date | datetime:"%Y-%m-%d" }}.

Your score: {{ score | default:"0" }}
"""
    
    context1 = {
        'name': 'John Doe',
        'date': datetime.now(),
        'score': 95
    }
    
    print("示例1：基本变量和过滤器")
    print("-" * 40)
    print(engine.render(template1, context1))
    print()
    
    # 示例2：条件语句
    template2 = """
{% if user.is_admin %}
Welcome, Administrator {{ user.name }}!
{% elif user.is_moderator %}
Welcome, Moderator {{ user.name }}!
{% else %}
Welcome, User {{ user.name }}!
{% endif %}

{% if items|length > 0 %}
You have {{ items|length }} items.
{% else %}
Your cart is empty.
{% endif %}
"""
    
    context2 = {
        'user': {
            'name': 'Alice',
            'is_admin': False,
            'is_moderator': True
        },
        'items': ['apple', 'banana', 'orange']
    }
    
    print("示例2：条件语句")
    print("-" * 40)
    print(engine.render(template2, context2))
    print()
    
    # 示例3：循环语句
    template3 = """
<h1>Product List</h1>
<ul>
{% for product in products %}
  <li>
    <strong>{{ product.name }}</strong> - ${{ product.price }}
    {% if product.in_stock %}
      (In Stock)
    {% else %}
      (Out of Stock)
    {% endif %}
  </li>
{% endfor %}
</ul>

<h2>Dictionary Items</h2>
<ul>
{% for key, value in settings %}
  <li>{{ key }}: {{ value }}</li>
{% endfor %}
</ul>
"""
    
    context3 = {
        'products': [
            {'name': 'Laptop', 'price': 999.99, 'in_stock': True},
            {'name': 'Mouse', 'price': 29.99, 'in_stock': False},
            {'name': 'Keyboard', 'price': 79.99, 'in_stock': True},
        ],
        'settings': {'theme': 'dark', 'language': 'en', 'notifications': True}
    }
    
    print("示例3：循环语句")
    print("-" * 40)
    print(engine.render(template3, context3))
    
    # 示例4：错误处理
    try:
        template4 = "{{ undefined_var | unknown_filter }}"
        engine.render(template4, {})
    except TemplateSyntaxError as e:
        print(f"\n示例4：错误处理 - {e}")
    
    # 自定义过滤器
    engine.register_filter('truncate', lambda s, length=50: s[:length] + '...' if len(s) > length else s)
    
    template5 = "{{ long_text | truncate:30 }}"
    context5 = {'long_text': 'This is a very long text that needs to be truncated.'}
    print(f"\n自定义过滤器: {engine.render(template5, context5)}")