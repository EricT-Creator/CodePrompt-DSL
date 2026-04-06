import re
import sys
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

class TemplateSyntaxError(Exception):
    """模板语法错误"""
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        if line is not None:
            message = f"第{line}行，第{column}列: {message}" if column else f"第{line}行: {message}"
        super().__init__(message)

class TokenType(Enum):
    TEXT = "TEXT"
    VARIABLE = "VARIABLE"
    IF_START = "IF_START"
    IF_END = "IF_END"
    FOR_START = "FOR_START"
    FOR_END = "FOR_END"
    FILTER = "FILTER"

@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: str
    line: int
    column: int

class FilterRegistry:
    """过滤器注册表"""
    
    def __init__(self):
        self.filters: Dict[str, Callable[[str], str]] = {}
        self.register_default_filters()
    
    def register_default_filters(self):
        """注册默认过滤器"""
        self.filters.update({
            "upper": lambda s: s.upper(),
            "lower": lambda s: s.lower(),
            "title": lambda s: s.title(),
            "capitalize": lambda s: s.capitalize(),
            "strip": lambda s: s.strip(),
            "length": lambda s: str(len(s)),
            "reverse": lambda s: s[::-1],
        })
    
    def register_filter(self, name: str, func: Callable[[str], str]):
        """注册自定义过滤器"""
        self.filters[name] = func
    
    def apply_filter(self, value: str, filter_name: str) -> str:
        """应用过滤器"""
        if filter_name not in self.filters:
            raise ValueError(f"未知的过滤器: {filter_name}")
        
        # 确保值是字符串
        if not isinstance(value, str):
            value = str(value)
        
        return self.filters[filter_name](value)
    
    def apply_filter_chain(self, value: str, filter_chain: List[str]) -> str:
        """应用过滤器链"""
        result = value
        for filter_name in filter_chain:
            result = self.apply_filter(result, filter_name.strip())
        return result

class TemplateLexer:
    """模板词法分析器"""
    
    def __init__(self):
        # 定义正则表达式模式
        self.patterns = [
            (r'{{', lambda m: TokenType.VARIABLE),
            (r'}}', lambda m: TokenType.VARIABLE),
            (r'{%\s*if\s+', lambda m: TokenType.IF_START),
            (r'{%\s*endif\s*%}', lambda m: TokenType.IF_END),
            (r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}', lambda m: TokenType.FOR_START),
            (r'{%\s*endfor\s*%}', lambda m: TokenType.FOR_END),
            (r'\|\s*(\w+)', lambda m: TokenType.FILTER),
        ]
        
        # 编译正则表达式
        self.compiled_patterns = []
        for pattern, token_type_func in self.patterns:
            self.compiled_patterns.append((re.compile(pattern), token_type_func))
    
    def tokenize(self, template: str) -> List[Token]:
        """将模板分词"""
        tokens = []
        lines = template.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            col = 0
            
            while col < len(line):
                matched = False
                
                # 尝试匹配模式
                for pattern, token_type_func in self.compiled_patterns:
                    match = pattern.match(line, col)
                    
                    if match:
                        # 添加之前的文本（如果有）
                        text_end = col
                        if text_end > 0 or (col == 0 and match.start() > 0):
                            text_token = Token(
                                type=TokenType.TEXT,
                                value=line[col:match.start()],
                                line=line_num,
                                column=col + 1
                            )
                            tokens.append(text_token)
                        
                        # 添加匹配的令牌
                        token = Token(
                            type=token_type_func(match),
                            value=match.group(),
                            line=line_num,
                            column=match.start() + 1
                        )
                        tokens.append(token)
                        
                        col = match.end()
                        matched = True
                        break
                
                if not matched:
                    # 如果没有匹配到模式，将当前字符作为文本
                    if not tokens or tokens[-1].type != TokenType.TEXT:
                        # 开始新的文本令牌
                        token = Token(
                            type=TokenType.TEXT,
                            value=line[col],
                            line=line_num,
                            column=col + 1
                        )
                        tokens.append(token)
                    else:
                        # 添加到现有的文本令牌
                        tokens[-1].value += line[col]
                    
                    col += 1
            
            # 添加换行符作为文本
            if line_num < len(lines):
                if tokens and tokens[-1].type == TokenType.TEXT:
                    tokens[-1].value += '\n'
                else:
                    tokens.append(Token(
                        type=TokenType.TEXT,
                        value='\n',
                        line=line_num,
                        column=len(line) + 1
                    ))
        
        return tokens

class TemplateNode:
    """模板节点基类"""
    pass

@dataclass
class TextNode(TemplateNode):
    """文本节点"""
    text: str

@dataclass
class VariableNode(TemplateNode):
    """变量节点"""
    name: str
    filters: List[str]

@dataclass
class IfNode(TemplateNode):
    """条件节点"""
    condition: str
    children: List[TemplateNode]
    else_children: List[TemplateNode] = None

@dataclass
class ForNode(TemplateNode):
    """循环节点"""
    item_var: str
    list_var: str
    children: List[TemplateNode]

class TemplateParser:
    """模板解析器"""
    
    def __init__(self):
        self.lexer = TemplateLexer()
        self.filter_registry = FilterRegistry()
    
    def parse(self, template: str) -> List[TemplateNode]:
        """解析模板"""
        tokens = self.lexer.tokenize(template)
        nodes, _ = self._parse_tokens(tokens, 0)
        return nodes
    
    def _parse_tokens(self, tokens: List[Token], position: int) -> tuple[List[TemplateNode], int]:
        """解析令牌序列"""
        nodes = []
        i = position
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == TokenType.TEXT:
                nodes.append(TextNode(text=token.value))
                i += 1
            
            elif token.type == TokenType.VARIABLE:
                # 解析变量
                if token.value == '{{':
                    # 寻找闭合的 }}
                    var_start = i
                    var_end = -1
                    depth = 0
                    
                    for j in range(i + 1, len(tokens)):
                        if tokens[j].type == TokenType.VARIABLE:
                            if tokens[j].value == '{{':
                                depth += 1
                            else:
                                depth -= 1
                                if depth == -1:
                                    var_end = j
                                    break
                    
                    if var_end == -1:
                        raise TemplateSyntaxError("未闭合的变量表达式", token.line, token.column)
                    
                    # 提取变量内容
                    var_content = ""
                    for j in range(var_start + 1, var_end):
                        var_content += tokens[j].value
                    
                    # 解析变量名和过滤器
                    variable_node = self._parse_variable(var_content, token.line)
                    nodes.append(variable_node)
                    
                    i = var_end + 1
            
            elif token.type == TokenType.IF_START:
                # 解析if语句
                condition = self._extract_condition(token.value)
                i += 1
                
                # 解析if块的主体
                children, new_i = self._parse_tokens(tokens, i)
                
                # 检查是否有else
                else_children = None
                if new_i < len(tokens) and tokens[new_i].type == TokenType.IF_START:
                    # 检查是否是else
                    if tokens[new_i].value.startswith('{% else'):
                        new_i += 1
                        else_children, new_i = self._parse_tokens(tokens, new_i)
                
                # 查找endif
                if new_i >= len(tokens) or tokens[new_i].type != TokenType.IF_END:
                    raise TemplateSyntaxError("if语句没有对应的endif", token.line, token.column)
                
                if_node = IfNode(
                    condition=condition,
                    children=children,
                    else_children=else_children
                )
                nodes.append(if_node)
                
                i = new_i + 1
            
            elif token.type == TokenType.FOR_START:
                # 解析for语句
                match = re.match(r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}', token.value)
                if not match:
                    raise TemplateSyntaxError("无效的for语句语法", token.line, token.column)
                
                item_var = match.group(1)
                list_var = match.group(2)
                
                i += 1
                
                # 解析for块的主体
                children, new_i = self._parse_tokens(tokens, i)
                
                # 查找endfor
                if new_i >= len(tokens) or tokens[new_i].type != TokenType.FOR_END:
                    raise TemplateSyntaxError("for语句没有对应的endfor", token.line, token.column)
                
                for_node = ForNode(
                    item_var=item_var,
                    list_var=list_var,
                    children=children
                )
                nodes.append(for_node)
                
                i = new_i + 1
            
            else:
                # 其他令牌（如过滤器）在解析变量时处理
                i += 1
        
        return nodes, i
    
    def _parse_variable(self, content: str, line: int) -> VariableNode:
        """解析变量表达式"""
        content = content.strip()
        
        # 分离变量名和过滤器
        parts = content.split('|')
        
        if not parts:
            raise TemplateSyntaxError("空的变量表达式", line)
        
        variable_name = parts[0].strip()
        filters = []
        
        if len(parts) > 1:
            filters = parts[1:]
        
        return VariableNode(
            name=variable_name,
            filters=filters
        )
    
    def _extract_condition(self, if_token: str) -> str:
        """从if令牌中提取条件"""
        # 移除 {% if 和 %}
        condition = if_token.replace('{%', '').replace('%}', '').replace('if', '')
        return condition.strip()

class TemplateEngine:
    """模板引擎"""
    
    def __init__(self):
        self.parser = TemplateParser()
        self.filter_registry = self.parser.filter_registry
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        渲染模板
        
        Args:
            template: 模板字符串
            context: 上下文字典
        
        Returns:
            str: 渲染结果
        
        Raises:
            TemplateSyntaxError: 如果模板语法错误
        """
        try:
            nodes = self.parser.parse(template)
            return self._render_nodes(nodes, context)
        
        except Exception as e:
            if isinstance(e, TemplateSyntaxError):
                raise
            raise TemplateSyntaxError(str(e))
    
    def _render_nodes(self, nodes: List[TemplateNode], context: Dict[str, Any]) -> str:
        """渲染节点列表"""
        result = []
        
        for node in nodes:
            if isinstance(node, TextNode):
                result.append(node.text)
            
            elif isinstance(node, VariableNode):
                value = self._get_variable_value(node.name, context)
                
                if node.filters:
                    value = self.filter_registry.apply_filter_chain(str(value), node.filters)
                
                result.append(str(value))
            
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, context):
                    result.append(self._render_nodes(node.children, context))
                elif node.else_children:
                    result.append(self._render_nodes(node.else_children, context))
            
            elif isinstance(node, ForNode):
                list_value = self._get_variable_value(node.list_var, context)
                
                if not isinstance(list_value, (list, tuple, range)):
                    raise TemplateSyntaxError(f"{node.list_var} 不是一个可迭代对象")
                
                for item in list_value:
                    # 创建新的上下文
                    new_context = context.copy()
                    new_context[node.item_var] = item
                    
                    result.append(self._render_nodes(node.children, new_context))
        
        return ''.join(result)
    
    def _get_variable_value(self, name: str, context: Dict[str, Any]) -> Any:
        """获取变量值（支持嵌套访问）"""
        if name in context:
            return context[name]
        
        # 尝试嵌套访问（如 user.name）
        parts = name.split('.')
        current = context
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                # 如果找不到，返回空字符串而不是抛出错误
                return ""
        
        return current
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        condition = condition.strip()
        
        # 简单条件：变量名（检查是否为真）
        if condition in context:
            value = context[condition]
            return bool(value)
        
        # 比较条件（如 x == 5, y != "text"）
        operators = ['==', '!=', '>=', '<=', '>', '<']
        
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left = left.strip()
                right = right.strip()
                
                left_value = self._get_variable_value(left, context)
                right_value = self._get_variable_value(right, context)
                
                # 类型转换
                try:
                    # 如果是数字，转换为数字
                    if isinstance(left_value, str) and left_value.replace('.', '', 1).isdigit():
                        left_value = float(left_value) if '.' in left_value else int(left_value)
                    if isinstance(right_value, str) and right_value.replace('.', '', 1).isdigit():
                        right_value = float(right_value) if '.' in right_value else int(right_value)
                except (ValueError, AttributeError):
                    pass
                
                if op == '==':
                    return left_value == right_value
                elif op == '!=':
                    return left_value != right_value
                elif op == '>=':
                    return left_value >= right_value
                elif op == '<=':
                    return left_value <= right_value
                elif op == '>':
                    return left_value > right_value
                elif op == '<':
                    return left_value < right_value
        
        # 布尔值
        if condition.lower() in ('true', 'false'):
            return condition.lower() == 'true'
        
        # 数字
        try:
            value = float(condition)
            return bool(value)
        except ValueError:
            pass
        
        # 字符串
        if condition.startswith('"') and condition.endswith('"'):
            return bool(condition[1:-1])
        
        # 默认返回False
        return False
    
    def register_filter(self, name: str, func: Callable[[str], str]):
        """注册自定义过滤器"""
        self.filter_registry.register_filter(name, func)

# 示例用法
def example_usage():
    """示例用法"""
    
    # 创建模板引擎
    engine = TemplateEngine()
    
    # 示例1：简单变量替换
    template1 = """
    Hello, {{ name }}!
    Welcome to {{ platform }}.
    Your account balance is: {{ balance | upper }}
    """
    
    context1 = {
        "name": "Alice",
        "platform": "Template Engine Demo",
        "balance": "$100.50"
    }
    
    print("示例1：简单变量替换")
    print("=" * 50)
    print(engine.render(template1, context1))
    
    # 示例2：条件语句
    template2 = """
    {% if user.logged_in %}
        Welcome back, {{ user.name }}!
        You have {{ user.messages }} new messages.
    {% else %}
        Please log in to continue.
    {% endif %}
    
    {% if show_banner %}
        <div class="banner">Special Offer!</div>
    {% endif %}
    """
    
    context2 = {
        "user": {
            "name": "Bob",
            "logged_in": True,
            "messages": 5
        },
        "show_banner": False
    }
    
    print("\n\n示例2：条件语句")
    print("=" * 50)
    print(engine.render(template2, context2))
    
    # 示例3：循环语句
    template3 = """
    <ul>
    {% for item in items %}
        <li>{{ item.name | title }} - ${{ item.price }}</li>
    {% endfor %}
    </ul>
    
    Total items: {{ items | length }}
    """
    
    context3 = {
        "items": [
            {"name": "apple", "price": 1.2},
            {"name": "banana", "price": 0.8},
            {"name": "orange", "price": 1.5},
            {"name": "grape", "price": 2.0},
        ]
    }
    
    print("\n\n示例3：循环语句")
    print("=" * 50)
    print(engine.render(template3, context3))
    
    # 示例4：嵌套结构和复杂条件
    template4 = """
    {% if users %}
        <h2>User List</h2>
        <table>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
            </tr>
            {% for user in users %}
                <tr>
                    <td>{{ user.name | capitalize }}</td>
                    <td>{{ user.email | lower }}</td>
                    <td>
                        {% if user.active %}
                            <span class="active">Active</span>
                        {% else %}
                            <span class="inactive">Inactive</span>
                        {% endif %}
                    </td>
                </tr>
            {% endfor %}
        </table>
    {% else %}
        <p>No users found.</p>
    {% endif %}
    """
    
    context4 = {
        "users": [
            {"name": "charlie", "email": "CHARLIE@EXAMPLE.COM", "active": True},
            {"name": "david", "email": "David@Example.Com", "active": False},
            {"name": "eve", "email": "EVE@EXAMPLE.COM", "active": True},
        ]
    }
    
    print("\n\n示例4：嵌套结构和复杂条件")
    print("=" * 50)
    print(engine.render(template4, context4))
    
    # 示例5：错误处理
    print("\n\n示例5：错误处理")
    print("=" * 50)
    
    invalid_template = """
    {% if missing_condition %}
        This will cause an error.
    {% endif %}
    {{ unclosed_variable
    """
    
    try:
        result = engine.render(invalid_template, {})
        print("渲染结果:", result)
    except TemplateSyntaxError as e:
        print(f"模板语法错误: {e}")
    
    # 示例6：注册自定义过滤器
    print("\n\n示例6：自定义过滤器")
    print("=" * 50)
    
    engine.register_filter("excited", lambda s: f"{s.upper()}!!!")
    
    template6 = "I am {{ feeling | excited }}"
    context6 = {"feeling": "happy"}
    
    print(engine.render(template6, context6))

# 测试错误处理
def test_error_handling():
    """测试错误处理"""
    print("\n\n错误处理测试")
    print("=" * 50)
    
    engine = TemplateEngine()
    
    test_cases = [
        ("未闭合变量", "{{ variable", "未闭合的变量表达式"),
        ("未闭合if", "{% if condition %}", "if语句没有对应的endif"),
        ("无效for语法", "{% for item in %}", "无效的for语句语法"),
        ("嵌套错误", "{% if x %}{% for y in z %}", "for语句没有对应的endfor"),
    ]
    
    for name, template, expected_error in test_cases:
        print(f"\n测试: {name}")
        try:
            result = engine.render(template, {})
            print(f"  错误：应该抛出异常但得到了: {result}")
        except TemplateSyntaxError as e:
            print(f"  正确捕获: {str(e)[:50]}...")
            if expected_error not in str(e):
                print(f"  警告：预期错误 '{expected_error}' 未在消息中")
        except Exception as e:
            print(f"  意外的异常类型: {type(e).__name__}: {e}")

# 性能测试
def performance_test():
    """性能测试"""
    print("\n\n性能测试")
    print("=" * 50)
    
    import time
    
    engine = TemplateEngine()
    
    # 复杂模板
    template = """
    {% for category in categories %}
        <h3>{{ category.name | upper }}</h3>
        <ul>
            {% for product in category.products %}
                <li>
                    <strong>{{ product.name | title }}</strong>: ${{ product.price }}
                    {% if product.stock > 0 %}
                        (In Stock)
                    {% else %}
                        (Out of Stock)
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    {% endfor %}
    """
    
    context = {
        "categories": [
            {
                "name": "electronics",
                "products": [
                    {"name": "laptop", "price": 999.99, "stock": 10},
                    {"name": "smartphone", "price": 699.99, "stock": 0},
                    {"name": "tablet", "price": 399.99, "stock": 25},
                ]
            },
            {
                "name": "books",
                "products": [
                    {"name": "fiction novel", "price": 19.99, "stock": 100},
                    {"name": "technical guide", "price": 49.99, "stock": 15},
                ]
            }
        ]
    }
    
    # 预热
    for _ in range(10):
        engine.render("{{ test }}", {"test": "warmup"})
    
    # 性能测试
    start_time = time.time()
    iterations = 1000
    
    for _ in range(iterations):
        result = engine.render(template, context)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"执行 {iterations} 次渲染:")
    print(f"  总耗时: {duration:.3f}秒")
    print(f"  平均每次: {duration/iterations*1000:.2f}毫秒")
    print(f"  每秒: {iterations/duration:.0f}次")

if __name__ == "__main__":
    print("模板引擎示例和测试")
    print("=" * 70)
    
    example_usage()
    test_error_handling()
    performance_test()