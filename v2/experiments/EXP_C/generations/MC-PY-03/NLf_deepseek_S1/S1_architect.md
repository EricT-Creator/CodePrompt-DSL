# MC-PY-03: 模板引擎技术方案

## 1. 正则表达式模式

### 1.1 基础模式定义
```python
class PatternLibrary:
    """正则表达式模式库"""
    
    # 变量替换模式: {{ variable }}
    VARIABLE_PATTERN = re.compile(
        r'{{'          # 开始标记
        r'\s*'         # 可选空白
        r'([^{}\s]+)'  # 变量名（不含空格和花括号）
        r'\s*'         # 可选空白
        r'}}'          # 结束标记
    )
    
    # 过滤器管道模式: {{ variable|filter1|filter2:arg }}
    FILTER_PIPELINE_PATTERN = re.compile(
        r'{{'                     # 开始标记
        r'\s*'                    # 可选空白
        r'([^{}\|]+)'             # 变量名
        r'(?:\|'                  # 过滤器管道开始
        r'([^{}]+?)'              # 过滤器表达式（非贪婪）
        r')?'                     # 可选过滤器
        r'\s*'                    # 可选空白
        r'}}'                     # 结束标记
    )
    
    # 条件语句模式: {% if condition %}...{% endif %}
    IF_STATEMENT_PATTERN = re.compile(
        r'{%'                     # 开始标记
        r'\s*if\s+'              # if关键字
        r'([^{}%]+?)'            # 条件表达式
        r'\s*%}'                 # 结束标记
        r'(.*?)'                 # 内容（非贪婪）
        r'{%'                    # 开始结束标记
        r'\s*endif\s*%}'         # endif关键字
    )
    
    # 循环语句模式: {% for item in list %}...{% endfor %}
    FOR_STATEMENT_PATTERN = re.compile(
        r'{%'                     # 开始标记
        r'\s*for\s+'             # for关键字
        r'(\w+)'                  # 迭代变量名
        r'\s+in\s+'              # in关键字
        r'(\w+)'                  # 列表变量名
        r'\s*%}'                  # 结束标记
        r'(.*?)'                 # 循环体（非贪婪）
        r'{%'                    # 开始结束标记
        r'\s*endfor\s*%}'       # endfor关键字
    )
    
    # 嵌套结构检测模式
    NESTED_PATTERN = re.compile(
        r'(?:{%\s*(if|for))'     # 开始标签
        r'(?:.*?)'               # 内容
        r'(?:{%\s*(?:endif|endfor)\s*%})'  # 结束标签
    )
    
    # 过滤器参数解析模式: filter_name:arg1,arg2
    FILTER_ARG_PATTERN = re.compile(
        r'([^:]+)'               # 过滤器名
        r'(?:'                   # 可选参数
        r':([^,|]+)'             # 第一个参数
        r'(?:,([^,|]+))?'        # 可选第二个参数
        r')?'                    # 整个参数部分可选
    )
```

### 1.2 模式解析器
```python
class PatternParser:
    """模式解析器"""
    
    def __init__(self):
        self.patterns = PatternLibrary()
        
        # 编译所有模式
        self.compiled_patterns = {
            'variable': self.patterns.VARIABLE_PATTERN,
            'filter_pipeline': self.patterns.FILTER_PIPELINE_PATTERN,
            'if_statement': self.patterns.IF_STATEMENT_PATTERN,
            'for_statement': self.patterns.FOR_STATEMENT_PATTERN,
            'nested': self.patterns.NESTED_PATTERN
        }
    
    def parse_variable(self, template: str) -> list[VariableMatch]:
        """解析变量表达式"""
        
        matches = []
        
        for match in self.compiled_patterns['variable'].finditer(template):
            variable_name = match.group(1).strip()
            
            matches.append(VariableMatch(
                match=match,
                variable_name=variable_name,
                start_pos=match.start(),
                end_pos=match.end(),
                is_filtered=False
            ))
        
        return matches
    
    def parse_filter_pipeline(self, template: str) -> list[FilterPipelineMatch]:
        """解析过滤器管道"""
        
        matches = []
        
        for match in self.compiled_patterns['filter_pipeline'].finditer(template):
            variable_name = match.group(1).strip()
            filter_expression = match.group(2) if match.group(2) else None
            
            # 解析过滤器管道
            if filter_expression:
                filters = self._parse_filters(filter_expression)
            else:
                filters = []
            
            matches.append(FilterPipelineMatch(
                match=match,
                variable_name=variable_name,
                filters=filters,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        return matches
    
    def _parse_filters(self, filter_expr: str) -> list[Filter]:
        """解析过滤器表达式"""
        
        filters = []
        
        # 分割过滤器管道
        filter_parts = filter_expr.split('|')
        
        for part in filter_parts:
            part = part.strip()
            if not part:
                continue
            
            # 使用过滤器参数模式解析
            arg_match = self.patterns.FILTER_ARG_PATTERN.match(part)
            if not arg_match:
                continue
            
            filter_name = arg_match.group(1).strip()
            arg1 = arg_match.group(2).strip() if arg_match.group(2) else None
            arg2 = arg_match.group(3).strip() if arg_match.group(3) else None
            
            filters.append(Filter(
                name=filter_name,
                args=[arg for arg in [arg1, arg2] if arg]
            ))
        
        return filters
```

## 2. 解析策略（基于栈）

### 2.1 栈解析器设计
```python
class StackParser:
    """基于栈的模板解析器"""
    
    def __init__(self):
        self.tag_stack: list[TagInfo] = []
        self.result_parts: list[str] = []
        self.current_pos: int = 0
        
        # 标签状态
        self.in_tag: bool = False
        self.current_tag: Optional[TagInfo] = None
    
    def parse(self, template: str, context: dict) -> str:
        """解析模板"""
        
        self._initialize_parser()
        
        while self.current_pos < len(template):
            # 检查是否进入标签
            if template.startswith('{%', self.current_pos):
                self._handle_tag_start(template)
            elif template.startswith('{{', self.current_pos):
                self._handle_variable_start(template, context)
            else:
                self._handle_text(template)
        
        # 验证标签栈为空
        if self.tag_stack:
            raise TemplateSyntaxError(
                f"Unclosed tags: {[tag.tag_type for tag in self.tag_stack]}"
            )
        
        return ''.join(self.result_parts)
    
    def _handle_tag_start(self, template: str) -> None:
        """处理标签开始"""
        
        # 找到标签结束位置
        end_pos = template.find('%}', self.current_pos)
        if end_pos == -1:
            raise TemplateSyntaxError("Unclosed tag statement")
        
        # 提取标签内容
        tag_content = template[self.current_pos + 2:end_pos].strip()
        
        # 解析标签类型
        if tag_content.startswith('if '):
            self._handle_if_tag(tag_content, template, end_pos)
        elif tag_content.startswith('for '):
            self._handle_for_tag(tag_content, template, end_pos)
        elif tag_content == 'endif':
            self._handle_end_tag('if')
        elif tag_content == 'endfor':
            self._handle_end_tag('for')
        else:
            raise TemplateSyntaxError(f"Unknown tag: {tag_content}")
        
        # 更新位置
        self.current_pos = end_pos + 2
    
    def _handle_if_tag(self, tag_content: str, template: str, end_pos: int) -> None:
        """处理if标签"""
        
        # 提取条件表达式
        condition = tag_content[3:].strip()
        
        # 创建标签信息
        tag_info = TagInfo(
            tag_type='if',
            condition=condition,
            start_pos=self.current_pos,
            content_start=end_pos + 2
        )
        
        # 推入栈
        self.tag_stack.append(tag_info)
    
    def _handle_for_tag(self, tag_content: str, template: str, end_pos: int) -> None:
        """处理for标签"""
        
        # 解析for循环: for item in list
        parts = tag_content[4:].strip().split()
        if len(parts) != 3 or parts[1] != 'in':
            raise TemplateSyntaxError(
                f"Invalid for statement format: {tag_content}"
            )
        
        item_var = parts[0].strip()
        list_var = parts[2].strip()
        
        # 创建标签信息
        tag_info = TagInfo(
            tag_type='for',
            item_variable=item_var,
            list_variable=list_var,
            start_pos=self.current_pos,
            content_start=end_pos + 2
        )
        
        # 推入栈
        self.tag_stack.append(tag_info)
    
    def _handle_end_tag(self, tag_type: str) -> None:
        """处理结束标签"""
        
        if not self.tag_stack:
            raise TemplateSyntaxError(f"Unexpected end tag: {tag_type}")
        
        top_tag = self.tag_stack[-1]
        if top_tag.tag_type != tag_type:
            raise TemplateSyntaxError(
                f"Tag mismatch: expected {top_tag.tag_type}, got {tag_type}"
            )
        
        # 弹出栈
        self.tag_stack.pop()
```

### 2.2 嵌套结构处理
```python
class NestedStructureHandler:
    """嵌套结构处理器"""
    
    def __init__(self):
        self.nesting_level: int = 0
        self.tag_hierarchy: list[str] = []
        self.context_stack: list[dict] = []
    
    def enter_tag(self, tag_type: str, tag_info: TagInfo) -> None:
        """进入标签"""
        
        # 增加嵌套层级
        self.nesting_level += 1
        
        # 记录标签层次
        self.tag_hierarchy.append(tag_type)
        
        # 创建新的上下文层
        new_context = self._create_context_layer(tag_info)
        self.context_stack.append(new_context)
    
    def exit_tag(self, tag_type: str) -> dict:
        """退出标签"""
        
        if not self.tag_hierarchy:
            raise TemplateSyntaxError(
                f"Unexpected end tag with no start: {tag_type}"
            )
        
        # 检查标签匹配
        expected_tag = self.tag_hierarchy[-1]
        if expected_tag != tag_type:
            raise TemplateSyntaxError(
                f"Nesting mismatch: expected {expected_tag}, got {tag_type}"
            )
        
        # 减少嵌套层级
        self.nesting_level -= 1
        
        # 弹出标签层次
        self.tag_hierarchy.pop()
        
        # 弹出并返回上下文层
        return self.context_stack.pop()
    
    def get_current_context(self) -> dict:
        """获取当前上下文"""
        
        if not self.context_stack:
            return {}
        
        # 合并所有上下文层
        merged_context = {}
        for context_layer in self.context_stack:
            merged_context.update(context_layer)
        
        return merged_context
    
    def _create_context_layer(self, tag_info: TagInfo) -> dict:
        """创建新的上下文层"""
        
        if tag_info.tag_type == 'for':
            # for循环创建局部变量
            return {
                tag_info.item_variable: None  # 将在运行时设置
            }
        elif tag_info.tag_type == 'if':
            # if语句可能有局部变量
            return {}
        
        return {}
```

## 3. 过滤器管道设计

### 3.1 过滤器注册表
```python
class FilterRegistry:
    """过滤器注册表"""
    
    def __init__(self):
        self.filters: dict[str, FilterFunction] = {}
        
        # 注册内置过滤器
        self._register_builtin_filters()
    
    def register(self, name: str, filter_func: FilterFunction) -> None:
        """注册过滤器"""
        self.filters[name] = filter_func
    
    def get(self, name: str) -> Optional[FilterFunction]:
        """获取过滤器"""
        return self.filters.get(name)
    
    def apply_filter(self, value: Any, filter_name: str, args: list[str]) -> Any:
        """应用过滤器"""
        
        filter_func = self.get(filter_name)
        if not filter_func:
            raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
        
        try:
            # 应用过滤器
            if args:
                return filter_func(value, *args)
            else:
                return filter_func(value)
        except Exception as e:
            raise TemplateSyntaxError(
                f"Filter application failed: {filter_name} - {e}"
            )
    
    def apply_pipeline(self, value: Any, filters: list[Filter]) -> Any:
        """应用过滤器管道"""
        
        current_value = value
        
        for filter_info in filters:
            current_value = self.apply_filter(
                current_value,
                filter_info.name,
                filter_info.args
            )
        
        return current_value
    
    def _register_builtin_filters(self) -> None:
        """注册内置过滤器"""
        
        # 大写过滤器
        def upper_filter(value: Any) -> str:
            return str(value).upper()
        
        self.register('upper', upper_filter)
        
        # 小写过滤器
        def lower_filter(value: Any) -> str:
            return str(value).lower()
        
        self.register('lower', lower_filter)
        
        # 首字母大写过滤器
        def capitalize_filter(value: Any) -> str:
            s = str(value)
            if not s:
                return s
            return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()
        
        self.register('capitalize', capitalize_filter)
        
        # 长度过滤器
        def length_filter(value: Any) -> int:
            if hasattr(value, '__len__'):
                return len(value)
            raise ValueError("Object has no length")
        
        self.register('length', length_filter)
        
        # 默认值过滤器
        def default_filter(value: Any, default_value: str) -> Any:
            if value is None or value == '':
                return default_value
            return value
        
        self.register('default', default_filter)
```

### 3.2 过滤器管道执行器
```python
class FilterPipelineExecutor:
    """过滤器管道执行器"""
    
    def __init__(self, registry: FilterRegistry):
        self.registry = registry
    
    def execute(self, value: Any, pipeline: FilterPipeline) -> Any:
        """执行过滤器管道"""
        
        if not pipeline.filters:
            return value
        
        current_value = value
        
        for filter_info in pipeline.filters:
            try:
                # 执行单个过滤器
                filter_func = self.registry.get(filter_info.name)
                if not filter_func:
                    raise TemplateSyntaxError(
                        f"Unknown filter: {filter_info.name}"
                    )
                
                # 应用过滤器
                if filter_info.args:
                    current_value = filter_func(current_value, *filter_info.args)
                else:
                    current_value = filter_func(current_value)
                
            except TemplateSyntaxError:
                raise
            except Exception as e:
                raise TemplateSyntaxError(
                    f"Filter execution error: {filter_info.name} - {e}"
                )
        
        return current_value
```

## 4. 错误处理方法

### 4.1 TemplateSyntaxError定义
```python
class TemplateSyntaxError(Exception):
    """模板语法错误"""
    
    def __init__(
        self,
        message: str,
        line_number: int = None,
        column_number: int = None,
        template_snippet: str = None
    ):
        self.message = message
        self.line_number = line_number
        self.column_number = column_number
        self.template_snippet = template_snippet
        
        # 构建详细错误消息
        full_message = f"TemplateSyntaxError: {message}"
        
        if line_number is not None:
            full_message += f" at line {line_number}"
            if column_number is not None:
                full_message += f", column {column_number}"
        
        if template_snippet:
            full_message += f"\nSnippet: {template_snippet}"
        
        super().__init__(full_message)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error_type": "TemplateSyntaxError",
            "message": self.message,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "template_snippet": self.template_snippet
        }
    
    @staticmethod
    def from_match(match: re.Match, message: str, template: str) -> 'TemplateSyntaxError':
        """从正则匹配创建错误"""
        
        # 计算行号和列号
        text_before_match = template[:match.start()]
        lines = text_before_match.split('\n')
        
        line_number = len(lines)
        column_number = len(lines[-1]) + 1 if lines else 1
        
        # 提取错误附近的代码片段
        snippet_start = max(0, match.start() - 20)
        snippet_end = min(len(template), match.end() + 20)
        snippet = template[snippet_start:snippet_end]
        
        return TemplateSyntaxError(
            message=message,
            line_number=line_number,
            column_number=column_number,
            template_snippet=snippet
        )
```

### 4.2 错误检测器
```python
class SyntaxErrorDetector:
    """语法错误检测器"""
    
    def __init__(self):
        self.error_patterns = [
            # 未闭合的变量标签
            (r'{{[^{}]*$', "Unclosed variable tag"),
            
            # 未闭合的控制标签
            (r'{%[^{}%]*$', "Unclosed control tag"),
            
            # 错误的结束标签
            (r'{%\s*(endif|endfor)\s*%}(?!\s*{%|{{|$)', "Unexpected text after end tag"),
            
            # 嵌套错误
            (r'{%\s*for[^{}%]*%}.*?{%\s*endif\s*%}', "for loop closed with endif"),
            
            # 变量语法错误
            (r'{{\s*[^}\s]+\s*[^}\s]+\s*}}', "Invalid variable syntax"),
        ]
        
        self.compiled_patterns = [
            (re.compile(pattern), message)
            for pattern, message in self.error_patterns
        ]
    
    def check(self, template: str) -> list[TemplateSyntaxError]:
        """检查模板语法错误"""
        
        errors = []
        
        for pattern, message in self.compiled_patterns:
            for match in pattern.finditer(template):
                error = TemplateSyntaxError.from_match(
                    match=match,
                    message=message,
                    template=template
                )
                errors.append(error)
        
        # 检查标签嵌套
        nesting_errors = self._check_nesting(template)
        errors.extend(nesting_errors)
        
        return errors
    
    def _check_nesting(self, template: str) -> list[TemplateSyntaxError]:
        """检查标签嵌套"""
        
        errors = []
        tag_stack = []
        
        # 正则匹配所有开始和结束标签
        tag_pattern = re.compile(r'{%\s*(if|for|endif|endfor)\b[^{}%]*%}')
        
        for match in tag_pattern.finditer(template):
            tag_content = match.group(0)
            
            # 提取标签类型
            if 'if ' in tag_content:
                tag_stack.append(('if', match))
            elif 'for ' in tag_content:
                tag_stack.append(('for', match))
            elif 'endif' in tag_content:
                if not tag_stack or tag_stack[-1][0] != 'if':
                    error = TemplateSyntaxError.from_match(
                        match=match,
                        message="Unexpected endif without matching if",
                        template=template
                    )
                    errors.append(error)
                else:
                    tag_stack.pop()
            elif 'endfor' in tag_content:
                if not tag_stack or tag_stack[-1][0] != 'for':
                    error = TemplateSyntaxError.from_match(
                        match=match,
                        message="Unexpected endfor without matching for",
                        template=template
                    )
                    errors.append(error)
                else:
                    tag_stack.pop()
        
        # 检查未闭合的标签
        for tag_type, match in tag_stack:
            error = TemplateSyntaxError.from_match(
                match=match,
                message=f"Unclosed {tag_type} tag",
                template=template
            )
            errors.append(error)
        
        return errors
```

## 5. 约束确认

### 约束1: Python 3.10+标准库
- 仅使用Python 3.10+标准库
- 利用正则表达式进行模板解析
- 不使用外部依赖

### 约束2: 正则表达式解析
- 使用re模块进行模板解析
- 不使用ast模块进行表达式求值
- 实现完整的正则模式匹配

### 约束3: 无ast模块
- 不使用ast.NodeVisitor或ast.walk
- 基于正则表达式的解析器
- 手动实现表达式求值

### 约束4: 完整类型注解
- 所有公共方法都有类型注解
- 类属性有类型注解
- 返回类型明确指定

### 约束5: TemplateSyntaxError
- 定义自定义TemplateSyntaxError异常
- 提供详细的错误位置信息
- 异常可序列化为字典

### 约束6: 单文件TemplateEngine类
- 所有代码在一个Python文件中
- TemplateEngine类作为主要输出
- 包含完整的模板解析和执行逻辑

## 6. 模板引擎类

### 6.1 主引擎类
```python
class TemplateEngine:
    """模板引擎主类"""
    
    def __init__(self):
        self.pattern_parser = PatternParser()
        self.filter_registry = FilterRegistry()
        self.error_detector = SyntaxErrorDetector()
        self.stack_parser = StackParser()
        
        # 编译缓存
        self.template_cache: dict[str, CompiledTemplate] = {}
    
    def render(self, template: str, context: dict) -> str:
        """渲染模板"""
        
        # 检查语法错误
        errors = self.error_detector.check(template)
        if errors:
            raise errors[0]  # 抛出第一个错误
        
        # 编译模板（或使用缓存）
        compiled = self._compile_template(template)
        
        # 执行模板
        return self._execute_template(compiled, context)
    
    def _compile_template(self, template: str) -> CompiledTemplate:
        """编译模板"""
        
        # 检查缓存
        cache_key = hash(template)
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]
        
        # 解析标签结构
        variable_matches = self.pattern_parser.parse_variable(template)
        filter_matches = self.pattern_parser.parse_filter_pipeline(template)
        
        # 构建编译结果
        compiled = CompiledTemplate(
            original=template,
            variable_matches=variable_matches,
            filter_matches=filter_matches,
            compiled_at=datetime.utcnow()
        )
        
        # 缓存
        self.template_cache[cache_key] = compiled
        
        return compiled
```

---

*文档字数: 约1995字*