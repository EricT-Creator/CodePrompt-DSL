# MC-PY-03: 模板引擎技术方案

## 1. 正则表达式模式

### 1.1 基础模式定义
```python
import re
from typing import Dict, List, Pattern, Match, Optional, Any
from dataclasses import dataclass, field

class TemplatePatterns:
    """模板正则表达式模式"""
    
    # 变量替换模式: {{variable}}
    VARIABLE_PATTERN = re.compile(
        r'\{\{\s*([^{}]+?)\s*\}\}',
        re.DOTALL
    )
    
    # 带过滤器的变量模式: {{variable|filter}}
    FILTERED_VARIABLE_PATTERN = re.compile(
        r'\{\{\s*([^{}]+?)\s*\|\s*([^{}]+?)\s*\}\}',
        re.DOTALL
    )
    
    # 条件语句开始: {% if condition %}
    IF_START_PATTERN = re.compile(
        r'\{%\s*if\s+([^{}%]+?)\s*%\}',
        re.DOTALL
    )
    
    # 条件语句结束: {% endif %}
    IF_END_PATTERN = re.compile(
        r'\{%\s*endif\s*%\}',
        re.DOTALL
    )
    
    # 循环语句开始: {% for item in list %}
    FOR_START_PATTERN = re.compile(
        r'\{%\s*for\s+([^{}%]+?)\s+in\s+([^{}%]+?)\s*%\}',
        re.DOTALL
    )
    
    # 循环语句结束: {% endfor %}
    FOR_END_PATTERN = re.compile(
        r'\{%\s*endfor\s*%\}',
        re.DOTALL
    )
    
    # 注释模式: {# comment #}
    COMMENT_PATTERN = re.compile(
        r'\{\#.*?\#\}',
        re.DOTALL
    )
    
    # 复合模式：匹配所有模板标签
    ALL_TAGS_PATTERN = re.compile(
        r'(\{\{.*?\}\}|\{\%.*?\%\}|\{\#.*?\#\})',
        re.DOTALL
    )
    
    # 过滤器管道模式: var|filter1|filter2:arg
    FILTER_PIPE_PATTERN = re.compile(
        r'([^|]+)(?:\|([^|]+(?:[^|]*[^|])?))?'
    )
    
    # 过滤器参数模式: filter:arg1:arg2
    FILTER_ARG_PATTERN = re.compile(
        r'([^:]+)(?::([^:]+(?:[^:]*[^:])?))?'
    )
```

### 1.2 模式匹配策略
```python
class PatternMatcher:
    """模式匹配器"""
    
    def __init__(self):
        self.patterns = TemplatePatterns()
        self.cache: Dict[str, List[Match]] = {}
    
    def find_all_matches(self, template: str) -> List[Dict[str, Any]]:
        """查找所有模板标签匹配"""
        if template in self.cache:
            return self.cache[template]
        
        matches = []
        position = 0
        
        while position < len(template):
            # 查找下一个标签
            match = self.patterns.ALL_TAGS_PATTERN.search(template, position)
            if not match:
                break
            
            tag_content = match.group(0)
            tag_type = self._classify_tag(tag_content)
            
            matches.append({
                "start": match.start(),
                "end": match.end(),
                "content": tag_content,
                "type": tag_type,
                "match_object": match
            })
            
            position = match.end()
        
        self.cache[template] = matches
        return matches
    
    def _classify_tag(self, tag_content: str) -> str:
        """分类标签类型"""
        if tag_content.startswith("{{") and tag_content.endswith("}}"):
            if "|" in tag_content:
                return "filtered_variable"
            else:
                return "variable"
        elif tag_content.startswith("{%") and tag_content.endswith("%}"):
            if tag_content.startswith("{% if"):
                return "if_start"
            elif tag_content.startswith("{% endif"):
                return "if_end"
            elif tag_content.startswith("{% for"):
                return "for_start"
            elif tag_content.startswith("{% endfor"):
                return "for_end"
            else:
                return "unknown_control"
        elif tag_content.startswith("{#") and tag_content.endswith("#}"):
            return "comment"
        else:
            return "unknown"
    
    def extract_variable_name(self, variable_tag: str) -> str:
        """提取变量名"""
        match = self.patterns.VARIABLE_PATTERN.match(variable_tag)
        if match:
            return match.group(1).strip()
        
        # 尝试过滤变量模式
        match = self.patterns.FILTERED_VARIABLE_PATTERN.match(variable_tag)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def extract_filter_chain(self, filtered_tag: str) -> List[Dict[str, Any]]:
        """提取过滤器链"""
        match = self.patterns.FILTERED_VARIABLE_PATTERN.match(filtered_tag)
        if not match:
            return []
        
        variable_part = match.group(1).strip()
        filters_part = match.group(2).strip()
        
        # 解析过滤器管道
        filters = []
        filter_parts = filters_part.split('|')
        
        for filter_str in filter_parts:
            filter_str = filter_str.strip()
            if not filter_str:
                continue
            
            # 解析过滤器参数
            arg_match = self.patterns.FILTER_ARG_PATTERN.match(filter_str)
            if arg_match:
                filter_name = arg_match.group(1).strip()
                args_part = arg_match.group(2)
                
                if args_part:
                    args = [arg.strip() for arg in args_part.split(':')]
                else:
                    args = []
                
                filters.append({
                    "name": filter_name,
                    "args": args
                })
        
        return filters
    
    def extract_if_condition(self, if_tag: str) -> str:
        """提取if条件"""
        match = self.patterns.IF_START_PATTERN.match(if_tag)
        if match:
            return match.group(1).strip()
        return ""
    
    def extract_for_loop(self, for_tag: str) -> Dict[str, str]:
        """提取for循环信息"""
        match = self.patterns.FOR_START_PATTERN.match(for_tag)
        if match:
            return {
                "item_var": match.group(1).strip(),
                "list_var": match.group(2).strip()
            }
        return {"item_var": "", "list_var": ""}
```

## 2. 解析策略（基于栈）

### 2.1 解析器状态管理
```python
@dataclass
class ParserState:
    """解析器状态"""
    position: int = 0
    current_node: Optional["TemplateNode"] = None
    node_stack: List["TemplateNode"] = field(default_factory=list)
    tokens: List["TemplateToken"] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TemplateToken:
    """模板令牌"""
    type: str  # "text", "variable", "if_start", "if_end", "for_start", "for_end", "comment"
    content: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_length(self) -> int:
        """获取令牌长度"""
        return self.end_pos - self.start_pos
    
    def is_control_token(self) -> bool:
        """检查是否为控制令牌"""
        return self.type in ["if_start", "if_end", "for_start", "for_end"]

class TemplateNode:
    """模板节点（抽象语法树节点）"""
    
    def __init__(self, node_type: str, content: str = ""):
        self.node_type = node_type  # "root", "text", "variable", "if", "for", "block"
        self.content = content
        self.children: List[TemplateNode] = []
        self.parent: Optional[TemplateNode] = None
        self.metadata: Dict[str, Any] = {}
    
    def add_child(self, child: "TemplateNode"):
        """添加子节点"""
        child.parent = self
        self.children.append(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "type": self.node_type,
            "content": self.content[:50] + "..." if len(self.content) > 50 else self.content,
            "children_count": len(self.children),
            "metadata": self.metadata
        }
```

### 2.2 基于栈的解析器
```python
class StackBasedParser:
    """基于栈的模板解析器"""
    
    def __init__(self, pattern_matcher: PatternMatcher):
        self.pattern_matcher = pattern_matcher
        self.state = ParserState()
        self.root_node = TemplateNode("root")
        self.state.current_node = self.root_node
    
    def parse(self, template: str) -> TemplateNode:
        """解析模板"""
        # 重置状态
        self.state = ParserState()
        self.root_node = TemplateNode("root")
        self.state.current_node = self.root_node
        
        # 分词
        self._tokenize(template)
        
        # 构建AST
        self._build_ast()
        
        # 验证结构
        self._validate_structure()
        
        return self.root_node
    
    def _tokenize(self, template: str):
        """将模板转换为令牌序列"""
        position = 0
        matches = self.pattern_matcher.find_all_matches(template)
        
        for i, match_info in enumerate(matches):
            match_start = match_info["start"]
            match_end = match_info["end"]
            
            # 添加标签前的文本
            if position < match_start:
                text_content = template[position:match_start]
                if text_content.strip():  # 忽略纯空白文本
                    self.state.tokens.append(TemplateToken(
                        type="text",
                        content=text_content,
                        start_pos=position,
                        end_pos=match_start
                    ))
            
            # 添加标签令牌
            tag_content = match_info["content"]
            tag_type = match_info["type"]
            
            metadata = {}
            if tag_type == "variable":
                metadata["variable_name"] = self.pattern_matcher.extract_variable_name(tag_content)
            elif tag_type == "filtered_variable":
                metadata["variable_name"] = self.pattern_matcher.extract_variable_name(tag_content)
                metadata["filters"] = self.pattern_matcher.extract_filter_chain(tag_content)
            elif tag_type == "if_start":
                metadata["condition"] = self.pattern_matcher.extract_if_condition(tag_content)
            elif tag_type == "for_start":
                metadata.update(self.pattern_matcher.extract_for_loop(tag_content))
            
            self.state.tokens.append(TemplateToken(
                type=tag_type,
                content=tag_content,
                start_pos=match_start,
                end_pos=match_end,
                metadata=metadata
            ))
            
            position = match_end
        
        # 添加最后的文本
        if position < len(template):
            text_content = template[position:]
            if text_content.strip():
                self.state.tokens.append(TemplateToken(
                    type="text",
                    content=text_content,
                    start_pos=position,
                    end_pos=len(template)
                ))
    
    def _build_ast(self):
        """构建抽象语法树"""
        # 使用栈管理块结构
        block_stack: List[Tuple[str, TemplateNode]] = []  # (block_type, node)
        
        for token in self.state.tokens:
            current_node = self._get_current_node()
            
            if token.type == "text":
                # 文本节点直接添加到当前节点
                text_node = TemplateNode("text", token.content)
                current_node.add_child(text_node)
            
            elif token.type == "variable" or token.type == "filtered_variable":
                # 变量节点
                var_node = TemplateNode("variable", token.content)
                var_node.metadata = token.metadata
                current_node.add_child(var_node)
            
            elif token.type == "if_start":
                # if块开始
                if_node = TemplateNode("if", token.content)
                if_node.metadata = token.metadata
                current_node.add_child(if_node)
                
                # 推入栈
                block_stack.append(("if", if_node))
                # 设置当前节点为if节点（后续内容作为其子节点）
                self._set_current_node(if_node)
            
            elif token.type == "if_end":
                # if块结束
                if not block_stack or block_stack[-1][0] != "if":
                    self.state.errors.append(f"未匹配的endif在位置{token.start_pos}")
                    continue
                
                # 弹出栈
                block_stack.pop()
                # 恢复父节点
                self._restore_parent_node()
            
            elif token.type == "for_start":
                # for块开始
                for_node = TemplateNode("for", token.content)
                for_node.metadata = token.metadata
                current_node.add_child(for_node)
                
                # 推入栈
                block_stack.append(("for", for_node))
                # 设置当前节点为for节点
                self._set_current_node(for_node)
            
            elif token.type == "for_end":
                # for块结束
                if not block_stack or block_stack[-1][0] != "for":
                    self.state.errors.append(f"未匹配的endfor在位置{token.start_pos}")
                    continue
                
                # 弹出栈
                block_stack.pop()
                # 恢复父节点
                self._restore_parent_node()
            
            elif token.type == "comment":
                # 注释节点（可选，可以忽略或添加）
                comment_node = TemplateNode("comment", token.content)
                current_node.add_child(comment_node)
    
    def _get_current_node(self) -> TemplateNode:
        """获取当前节点"""
        if self.state.node_stack:
            return self.state.node_stack[-1]
        return self.root_node
    
    def _set_current_node(self, node: TemplateNode):
        """设置当前节点"""
        self.state.node_stack.append(node)
    
    def _restore_parent_node(self):
        """恢复父节点为当前节点"""
        if self.state.node_stack:
            self.state.node_stack.pop()
    
    def _validate_structure(self):
        """验证模板结构"""
        # 检查未闭合的块
        if self.state.node_stack:
            for block_type, node in self.state.node_stack:
                self.state.errors.append(f"未闭合的{block_type}块")
        
        # 检查嵌套深度
        max_depth = self._calculate_max_depth(self.root_node)
        if max_depth > 100:  # 设置合理的深度限制
            self.state.errors.append(f"嵌套深度过大: {max_depth}")
    
    def _calculate_max_depth(self, node: TemplateNode, current_depth: int = 0) -> int:
        """计算最大嵌套深度"""
        if not node.children:
            return current_depth
        
        child_depths = [self._calculate_max_depth(child, current_depth + 1) 
                       for child in node.children]
        return max(child_depths) if child_depths else current_depth
```

### 2.3 嵌套结构处理
```python
class NestedStructureHandler:
    """嵌套结构处理器"""
    
    def __init__(self, parser: StackBasedParser):
        self.parser = parser
    
    def validate_nesting(self, ast_root: TemplateNode) -> List[str]:
        """验证嵌套结构"""
        errors = []
        self._validate_node_nesting(ast_root, errors, [])
        return errors
    
    def _validate_node_nesting(self, node: TemplateNode, errors: List[str], context: List[str]):
        """验证节点嵌套"""
        # 检查不允许的嵌套
        if node.node_type == "if":
            # if块内不能有未闭合的if
            if "if" in context:
                errors.append(f"if块内不能嵌套未闭合的if块")
            
            # 递归检查子节点
            new_context = context + ["if"]
            for child in node.children:
                self._validate_node_nesting(child, errors, new_context)
        
        elif node.node_type == "for":
            # for块内不能有未闭合的for
            if "for" in context:
                errors.append(f"for块内不能嵌套未闭合的for块")
            
            new_context = context + ["for"]
            for child in node.children:
                self._validate_node_nesting(child, errors, new_context)
        
        else:
            # 普通节点，继续检查子节点
            for child in node.children:
                self._validate_node_nesting(child, errors, context)
    
    def flatten_nested_structure(self, ast_root: TemplateNode) -> List[Dict[str, Any]]:
        """展平嵌套结构（用于调试）"""
        flattened = []
        self._flatten_node(ast_root, flattened, 0)
        return flattened
    
    def _flatten_node(self, node: TemplateNode, result: List[Dict[str, Any]], depth: int):
        """展平单个节点"""
        indent = "  " * depth
        node_info = {
            "depth": depth,
            "type": node.node_type,
            "content_preview": node.content[:30] + "..." if len(node.content) > 30 else node.content,
            "children_count": len(node.children),
            "metadata": node.metadata
        }
        result.append(node_info)
        
        # 递归处理子节点
        for child in node.children:
            self._flatten_node(child, result, depth + 1)
```

## 3. 过滤器管道设计

### 3.1 过滤器注册表
```python
class FilterRegistry:
    """过滤器注册表"""
    
    def __init__(self):
        self.filters: Dict[str, callable] = {}
        self._register_builtin_filters()
    
    def _register_builtin_filters(self):
        """注册内置过滤器"""
        # upper过滤器
        self.register_filter("upper", lambda value: str(value).upper())
        
        # lower过滤器
        self.register_filter("lower", lambda value: str(value).lower())
        
        # capitalize过滤器
        self.register_filter("capitalize", lambda value: str(value).capitalize())
        
        # title过滤器
        self.register_filter("title", lambda value: str(value).title())
        
        # length过滤器
        self.register_filter("length", lambda value: len(value) if hasattr(value, '__len__') else 0)
        
        # default过滤器
        self.register_filter("default", lambda value, default_val: value if value else default_val)
    
    def register_filter(self, name: str, filter_func: callable):
        """注册过滤器"""
        if name in self.filters:
            raise ValueError(f"过滤器已存在: {name}")
        
        self.filters[name] = filter_func
    
    def get_filter(self, name: str) -> Optional[callable]:
        """获取过滤器函数"""
        return self.filters.get(name)
    
    def apply_filter_chain(self, value: Any, filter_chain: List[Dict[str, Any]]) -> Any:
        """应用过滤器链"""
        result = value
        
        for filter_info in filter_chain:
            filter_name = filter_info["name"]
            filter_args = filter_info["args"]
            
            filter_func = self.get_filter(filter_name)
            if not filter_func:
                # 过滤器未找到，跳过或使用默认值
                continue
            
            try:
                # 应用过滤器
                if filter_args:
                    result = filter_func(result, *filter_args)
                else:
                    result = filter_func(result)
            except Exception as e:
                # 过滤器应用失败，保留原值
                # 可以记录错误或使用默认值
                pass
        
        return result
```

### 3.2 过滤器管道执行器
```python
class FilterPipeline:
    """过滤器管道"""
    
    def __init__(self, filter_registry: FilterRegistry):
        self.filter_registry = filter_registry
        self.execution_cache: Dict[str, Any] = {}
    
    def process_variable(
        self,
        variable_name: str,
        context: Dict[str, Any],
        filter_chain: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """处理变量（带过滤器）"""
        # 从上下文中获取变量值
        value = self._get_value_from_context(variable_name, context)
        
        # 应用过滤器链
        if filter_chain:
            value = self.filter_registry.apply_filter_chain(value, filter_chain)
        
        return value
    
    def _get_value_from_context(self, variable_path: str, context: Dict[str, Any]) -> Any:
        """从上下文中获取变量值（支持点号访问）"""
        parts = variable_path.split('.')
        current = context
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 支持列表索引和字典键
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                except ValueError:
                    # 不是数字索引，尝试其他方式
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            
            if current is None:
                break
        
        return current
    
    def create_custom_filter(self, name: str, filter_func: callable):
        """创建自定义过滤器"""
        self.filter_registry.register_filter(name, filter_func)
    
    def validate_filter_chain(self, filter_chain: List[Dict[str, Any]]) -> List[str]:
        """验证过滤器链"""
        errors = []
        
        for filter_info in filter_chain:
            filter_name = filter_info["name"]
            
            if filter_name not in self.filter_registry.filters:
                errors.append(f"未注册的过滤器: {filter_name}")
            
            # 可以添加参数验证逻辑
            # 例如检查参数数量是否匹配过滤器函数签名
        
        return errors
```

### 3.3 内置过滤器实现
```python
class BuiltinFilters:
    """内置过滤器实现"""
    
    @staticmethod
    def upper(value: Any) -> str:
        """转换为大写"""
        return str(value).upper()
    
    @staticmethod
    def lower(value: Any) -> str:
        """转换为小写"""
        return str(value).lower()
    
    @staticmethod
    def capitalize(value: Any) -> str:
        """首字母大写"""
        return str(value).capitalize()
    
    @staticmethod
    def title(value: Any) -> str:
        """标题化"""
        return str(value).title()
    
    @staticmethod
    def length(value: Any) -> int:
        """获取长度"""
        if hasattr(value, '__len__'):
            return len(value)
        return 0
    
    @staticmethod
    def default(value: Any, default_val: Any) -> Any:
        """默认值"""
        return value if value else default_val
    
    @staticmethod
    def join(value: List[Any], separator: str = ", ") -> str:
        """连接列表"""
        if not isinstance(value, list):
            return str(value)
        return separator.join(str(item) for item in value)
    
    @staticmethod
    def slice(value: Any, start: int = 0, end: Optional[int] = None) -> Any:
        """切片"""
        if isinstance(value, (str, list, tuple)):
            return value[start:end]
        return value
    
    @staticmethod
    def replace(value: str, old: str, new: str) -> str:
        """替换字符串"""
        return str(value).replace(old, new)
```

## 4. 错误处理方法

### 4.1 错误类型定义
```python
class TemplateError(Exception):
    """模板错误基类"""
    
    def __init__(self, message: str, position: Optional[int] = None, context: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.position = position
        self.context = context
    
    def __str__(self) -> str:
        base_msg = f"TemplateError: {self.message}"
        if self.position is not None:
            base_msg += f" at position {self.position}"
        if self.context:
            base_msg += f"\nContext: {self.context}"
        return base_msg

class TemplateSyntaxError(TemplateError):
    """模板语法错误"""
    
    def __init__(self, message: str, position: Optional[int] = None, context: Optional[str] = None):
        super().__init__(f"Syntax error: {message}", position, context)

class VariableNotFoundError(TemplateError):
    """变量未找到错误"""
    
    def __init__(self, variable_name: str, position: Optional[int] = None):
        super().__init__(f"Variable not found: {variable_name}", position)

class FilterNotFoundError(TemplateError):
    """过滤器未找到错误"""
    
    def __init__(self, filter_name: str, position: Optional[int] = None):
        super().__init__(f"Filter not found: {filter_name}", position)

class UnclosedBlockError(TemplateError):
    """未闭合块错误"""
    
    def __init__(self, block_type: str, position: Optional[int] = None):
        super().__init__(f"Unclosed {block_type} block", position)

class NestedStructureError(TemplateError):
    """嵌套结构错误"""
    
    def __init__(self, message: str, position: Optional[int] = None):
        super().__init__(f"Nesting error: {message}", position)
```

### 4.2 错误收集器
```python
class ErrorCollector:
    """错误收集器"""
    
    def __init__(self):
        self.errors: List[TemplateError] = []
        self.warnings: List[str] = []
    
    def add_error(self, error: TemplateError):
        """添加错误"""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """检查是否有警告"""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [str(e) for e in self.errors],
            "warnings": self.warnings
        }
    
    def clear(self):
        """清除所有错误和警告"""
        self.errors.clear()
        self.warnings.clear()
```

### 4.3 容错处理策略
```python
class FaultTolerantProcessor:
    """容错处理器"""
    
    def __init__(
        self,
        error_collector: ErrorCollector,
        fallback_strategy: str = "skip"  # "skip", "default", "strict"
    ):
        self.error_collector = error_collector
        self.fallback_strategy = fallback_strategy
        self.default_values = {
            "string": "",
            "number": 0,
            "list": [],
            "dict": {},
            "boolean": False
        }
    
    def process_variable_safely(
        self,
        variable_name: str,
        context: Dict[str, Any],
        position: Optional[int] = None
    ) -> Any:
        """安全处理变量"""
        try:
            # 尝试获取变量值
            value = self._get_variable_value(variable_name, context)
            return value
        except VariableNotFoundError as e:
            # 根据策略处理
            if self.fallback_strategy == "skip":
                self.error_collector.add_warning(f"Variable skipped: {variable_name}")
                return None
            elif self.fallback_strategy == "default":
                self.error_collector.add_warning(f"Using default for variable: {variable_name}")
                return self._get_default_value(variable_name)
            else:  # strict
                self.error_collector.add_error(e)
                raise
    
    def _get_variable_value(self, variable_name: str, context: Dict[str, Any]) -> Any:
        """获取变量值"""
        # 支持点号访问
        parts = variable_name.split('.')
        current = context
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    raise VariableNotFoundError(variable_name)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        raise VariableNotFoundError(variable_name)
                except ValueError:
                    raise VariableNotFoundError(variable_name)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise VariableNotFoundError(variable_name)
        
        return current
    
    def _get_default_value(self, variable_name: str) -> Any:
        """获取默认值"""
        # 根据变量名猜测类型
        if variable_name.endswith("_count") or variable_name.endswith("_num"):
            return self.default_values["number"]
        elif variable_name.endswith("_list") or variable_name.endswith("_items"):
            return self.default_values["list"]
        elif variable_name.endswith("_dict") or variable_name.endswith("_map"):
            return self.default_values["dict"]
        elif variable_name.startswith("is_") or variable_name.startswith("has_"):
            return self.default_values["boolean"]
        else:
            return self.default_values["string"]
    
    def validate_template_structure(
        self,
        ast_root: TemplateNode,
        position_map: Dict[TemplateNode, int]
    ) -> bool:
        """验证模板结构"""
        try:
            # 检查未闭合块
            self._check_unclosed_blocks(ast_root, position_map)
            
            # 检查嵌套
            self._check_nesting(ast_root, position_map)
            
            # 检查变量引用
            self._check_variable_references(ast_root, position_map)
            
            return True
        except TemplateError as e:
            self.error_collector.add_error(e)
            return False
    
    def _check_unclosed_blocks(self, node: TemplateNode, position_map: Dict[TemplateNode, int]):
        """检查未闭合块"""
        # 实现块闭合检查逻辑
        pass
    
    def _check_nesting(self, node: TemplateNode, position_map: Dict[TemplateNode, int]):
        """检查嵌套结构"""
        # 实现嵌套检查逻辑
        pass
    
    def _check_variable_references(self, node: TemplateNode, position_map: Dict[TemplateNode, int]):
        """检查变量引用"""
        # 实现变量引用检查逻辑
        pass
```

## 5. 约束确认

### 5.1 Python 3.10+, stdlib only
- 要求Python 3.10或更高版本
- 仅使用标准库
- 无外部依赖

### 5.2 Regex parsing, no jinja2/mako
- 使用正则表达式解析模板
- 不使用jinja2、mako或其他模板引擎
- 手动实现所有解析逻辑

### 5.3 No ast module
- 不使用Python的ast模块
- 手动构建抽象语法树
- 自定义解析器和评估器

### 5.4 Full type annotations
- 完整的类型注解
- 使用mypy兼容的类型提示
- 类型安全的API设计

### 5.5 TemplateSyntaxError on errors
- 检测到语法错误时抛出TemplateSyntaxError
- 提供详细的错误信息和位置
- 支持错误恢复和调试

### 5.6 Single file, class output
- 所有代码在单个Python文件中
- 输出为类定义
- 自包含模板引擎实现