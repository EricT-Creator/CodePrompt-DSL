# MC-PY-03: 模板引擎技术方案

## 项目概述
本方案设计一个轻量级模板引擎，支持变量替换、条件语句、循环结构和过滤器管道。引擎使用正则表达式解析模板语法，实现完整的模板编译和执行流程，支持嵌套结构和自定义过滤器。

## 约束解析
根据Header约束，本方案需满足以下技术要求：

| 约束 | 含义 | 技术实现 |
|------|------|----------|
| `[L]PY310` | Python 3.10+版本 | 使用Python 3.10+语法特性，如match语句、类型联合运算符 |
| `[D]STDLIB_ONLY` | 仅使用Python标准库 | 仅依赖`re`, `typing`, `collections`, `functools`等标准库 |
| `[!D]NO_TMPL_LIB` | 禁止使用模板引擎库 | 不依赖Jinja2、Mako等第三方模板库 |
| `[PARSE]REGEX` | 使用正则表达式进行模板解析 | 使用`re`模块定义语法模式，解析模板结构 |
| `[!D]NO_AST` | 禁止使用AST模块 | 不使用`ast`模块，通过正则和字符串操作实现 |
| `[TYPE]FULL_HINTS` | 完整的类型提示 | 所有函数、变量都有详细类型注解 |
| `[ERR]SYNTAX_EXC` | 语法错误时抛出SyntaxError异常 | 自定义`TemplateSyntaxError`异常，继承SyntaxError |
| `[O]CLASS` | 使用类实现 | 所有功能封装在类中 |
| `[FILE]SINGLE` | 单文件实现 | 所有代码在一个.py文件中 |

## 架构设计

### 1. 核心类架构

#### TemplateEngine类
主类，负责模板的编译和执行：
- `__init__()`: 初始化引擎，注册默认过滤器
- `compile()`: 编译模板字符串为可执行代码
- `render()`: 渲染模板，返回结果字符串
- `register_filter()`: 注册自定义过滤器

#### Template类
编译后的模板对象：
- `source`: 原始模板字符串
- `compiled_code`: 编译后的Python代码
- `filters`: 可用过滤器映射
- `render()`: 执行编译代码，返回渲染结果

#### TemplateSyntaxError类
自定义语法错误异常：
- `message`: 错误描述
- `lineno`: 错误行号
- `offset`: 错误位置偏移
- `source_line`: 错误行内容

### 2. 语法定义

#### 支持的语法结构
1. **变量替换**: `{{ variable }}`
2. **条件语句**: `{% if condition %}...{% endif %}`
3. **循环结构**: `{% for item in list %}...{% endfor %}`
4. **过滤器管道**: `{{ variable|filter1|filter2:arg }}`
5. **注释**: `{# comment #}`

#### 正则表达式模式
```python
# 变量模式
VAR_PATTERN = r'\{\{\s*([^|}]+?)(?:\s*\|\s*([^}]+))?\s*\}\}'

# 条件开始
IF_START_PATTERN = r'\{%\s*if\s+([^%]+)\s*%\}'

# 条件结束
IF_END_PATTERN = r'\{%\s*endif\s*%\}'

# 循环开始
FOR_START_PATTERN = r'\{%\s*for\s+(\w+)\s+in\s+([^%]+)\s*%\}'

# 循环结束
FOR_END_PATTERN = r'\{%\s*endfor\s*%\}'

# 注释
COMMENT_PATTERN = r'\{#.*?#\}'
```

### 3. 解析策略

#### 递归下降解析器
使用栈式解析器处理嵌套结构：

**解析流程**：
1. 扫描模板字符串，识别所有语法标记
2. 构建标记流（token stream）
3. 使用栈管理嵌套结构（if/for）
4. 验证语法正确性（匹配的起始/结束标记）
5. 生成抽象语法树（AST）表示

#### 标记数据结构
```python
from typing import TypedDict, Literal

class Token(TypedDict):
    """语法标记"""
    type: Literal['var', 'if_start', 'if_end', 'for_start', 'for_end', 'text', 'comment']
    value: str
    position: int  # 在源字符串中的位置
    lineno: int    # 行号
```

### 4. 编译策略

#### 代码生成算法
模板编译为Python函数：

**编译步骤**：
1. 解析模板为标记流
2. 构建嵌套结构树
3. 遍历结构树，生成Python代码
4. 包装为可执行函数

**生成代码结构**：
```python
def render_template(context):
    output_parts = []
    
    # 处理文本和变量
    output_parts.append("Hello, ")
    output_parts.append(str(context.get('name', '')))
    
    # 处理条件语句
    if context.get('show_list', False):
        output_parts.append("\nItems:")
        # 处理循环
        for item in context.get('items', []):
            output_parts.append(f"\n- {item}")
    
    return ''.join(output_parts)
```

#### 过滤器管道编译
过滤器链编译为函数调用链：

**转换规则**：
- `{{ name|upper }}` → `filters['upper'](context['name'])`
- `{{ name|default:"Guest" }}` → `filters['default'](context['name'], "Guest")`
- `{{ name|truncate:10|upper }}` → `filters['upper'](filters['truncate'](context['name'], 10))`

### 5. 过滤器系统

#### 内置过滤器
1. **`upper`**: 转换为大写
2. **`lower`**: 转换为小写
3. **`capitalize`**: 首字母大写
4. **`default`**: 提供默认值
5. **`length`**: 获取长度
6. **`truncate`**: 截断字符串

#### 过滤器接口
```python
from typing import Callable, Any

FilterFunc = Callable[..., str]

class FilterRegistry:
    """过滤器注册表"""
    def __init__(self):
        self._filters: Dict[str, FilterFunc] = {}
    
    def register(self, name: str, func: FilterFunc):
        self._filters[name] = func
    
    def get(self, name: str) -> FilterFunc:
        return self._filters.get(name)
```

## 关键实现策略

### 1. 正则表达式优化
- 预编译所有正则模式
- 使用非贪婪匹配避免过度匹配
- 正则缓存提高性能

### 2. 嵌套结构处理
- 使用栈跟踪嵌套层级
- 验证起始/结束标记匹配
- 支持多层嵌套（if within for within if）

### 3. 错误恢复
- 提供详细的错误位置信息
- 语法高亮显示错误行
- 建议可能的修复方案

### 4. 性能优化
- 模板编译缓存
- 字节码缓存
- 惰性求值优化

## 约束确认

### Constraint Acknowledgment

1. **`[L]PY310`** ✅
   - 方案使用Python 3.10+的`typing`语法
   - 使用`Literal`类型定义标记类型
   - 使用类型联合运算符

2. **`[D]STDLIB_ONLY`** ✅
   - 仅使用Python标准库：`re`, `typing`, `collections`, `functools`
   - 不依赖任何第三方库
   - 所有功能基于标准库实现

3. **`[!D]NO_TMPL_LIB`** ✅
   - 完全避免使用Jinja2、Mako等模板引擎库
   - 手动实现所有模板解析和渲染逻辑
   - 不导入任何第三方模板相关模块

4. **`[PARSE]REGEX`** ✅
   - 使用`re`模块定义所有语法模式
   - 正则表达式解析模板标记
   - 基于正则的语法验证

5. **`[!D]NO_AST`** ✅
   - 不使用`ast`模块进行代码分析
   - 通过字符串操作和正则实现编译
   - 手动构建抽象语法表示

6. **`[TYPE]FULL_HINTS`** ✅
   - 所有函数参数和返回值都有完整类型注解
   - 使用`TypedDict`定义数据结构
   - 变量声明包含类型提示
   - 泛型类型参数

7. **`[ERR]SYNTAX_EXC`** ✅
   - 定义`TemplateSyntaxError`异常类，继承`SyntaxError`
   - 语法错误时抛出该异常
   - 异常包含详细的位置信息和错误描述

8. **`[O]CLASS`** ✅
   - 主要功能封装在`TemplateEngine`类中
   - `Template`类表示编译后的模板
   - `FilterRegistry`类管理过滤器
   - 所有算法作为类方法实现

9. **`[FILE]SINGLE`** ✅
   - 所有代码实现在单个`.py`文件中
   - 包含所有类、函数和类型定义
   - 自包含，无需外部模块

## 安全考虑

### 1. 代码注入防护
- 限制可访问的上下文变量
- 沙箱执行环境
- 输入验证和转义

### 2. 资源限制
- 模板大小限制
- 递归深度限制
- 执行时间限制

### 3. 过滤器安全
- 过滤器参数验证
- 防止无限循环
- 内存使用限制

## 扩展功能

### 1. 模板继承
- 支持基模板和子模板
- 块覆盖机制
- 模板包含

### 2. 国际化支持
- 多语言模板
- 本地化过滤器
- 日期/数字格式化

### 3. 调试工具
- 语法高亮
- 执行跟踪
- 性能分析

## 性能优化

### 1. 编译缓存
- 基于模板内容的哈希缓存
- LRU缓存策略
- 缓存失效机制

### 2. 字节码优化
- 预编译为字节码
- 常量折叠
- 死代码消除

### 3. 内存优化
- 字符串构建器模式
- 生成器表达式
- 内存池管理

## 使用示例

### 基本使用
```python
engine = TemplateEngine()

# 编译模板
template = engine.compile("""
Hello, {{ name|capitalize }}!

{% if items %}
Your items:
{% for item in items %}
- {{ item|upper }}
{% endfor %}
{% endif %}
""")

# 渲染模板
context = {
    'name': 'john doe',
    'items': ['apple', 'banana', 'cherry']
}
result = template.render(context)
print(result)
```

### 自定义过滤器
```python
engine.register_filter('reverse', lambda s: s[::-1])
engine.register_filter('repeat', lambda s, times: s * int(times))

template = engine.compile("{{ text|reverse|repeat:3 }}")
result = template.render({'text': 'abc'})
# 输出: 'cbacbacba'
```

## 总结
本技术方案设计了一个符合所有Header约束的模板引擎。通过正则表达式解析、手动代码生成和完整的类型系统，实现了安全、高效的模板渲染功能。方案严格遵循约束要求，同时提供了良好的扩展性、安全性和性能表现。