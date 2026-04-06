# MC-PY-04: Python代码检查器技术方案

## 1. AST访问者类层次结构

### 1.1 基础访问者类
```python
class BaseVisitor(ast.NodeVisitor):
    """基础AST访问者"""
    
    def __init__(self):
        self.results: list[CheckResult] = []
        self.current_scope: Scope = Scope()
        self.scope_stack: list[Scope] = []
        
        # 符号表
        self.symbol_table: SymbolTable = SymbolTable()
        
        # 当前上下文
        self.current_module: str = "module"
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        
        # 统计信息
        self.stats: Statistics = Statistics()
    
    def visit(self, node: ast.AST) -> None:
        """访问节点"""
        
        # 更新当前节点信息
        self._update_context(node)
        
        # 调用父类方法
        super().visit(node)
    
    def _update_context(self, node: ast.AST) -> None:
        """更新当前上下文"""
        
        # 记录节点位置
        if hasattr(node, 'lineno'):
            self.current_line = node.lineno
            self.current_col = getattr(node, 'col_offset', 0)
        
        # 根据节点类型更新上下文
        if isinstance(node, ast.FunctionDef):
            self.current_function = node.name
            self._enter_function_scope(node)
            
        elif isinstance(node, ast.AsyncFunctionDef):
            self.current_function = node.name
            self._enter_function_scope(node)
            
        elif isinstance(node, ast.ClassDef):
            self.current_class = node.name
            self._enter_class_scope(node)
            
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # 这些节点结束时需要退出作用域
            self._exit_scope_on_finish = True
    
    def _enter_function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """进入函数作用域"""
        
        # 创建新作用域
        new_scope = Scope(
            parent=self.current_scope,
            scope_type=ScopeType.FUNCTION,
            name=node.name
        )
        
        # 推入作用域栈
        self.scope_stack.append(self.current_scope)
        self.current_scope = new_scope
        
        # 记录函数开始
        self._record_function_start(node)
    
    def _enter_class_scope(self, node: ast.ClassDef) -> None:
        """进入类作用域"""
        
        # 创建新作用域
        new_scope = Scope(
            parent=self.current_scope,
            scope_type=ScopeType.CLASS,
            name=node.name
        )
        
        # 推入作用域栈
        self.scope_stack.append(self.current_scope)
        self.current_scope = new_scope
```

### 1.2 专用访问者类
```python
class ImportVisitor(BaseVisitor):
    """导入语句访问者"""
    
    def visit_Import(self, node: ast.Import) -> None:
        """访问导入语句"""
        
        for alias in node.names:
            # 记录导入
            import_info = ImportInfo(
                module_name=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
                column_offset=node.col_offset
            )
            
            self.symbol_table.add_import(import_info)
            
            # 添加到当前作用域
            symbol_name = alias.asname or alias.name.split('.')[-1]
            self.current_scope.add_symbol(
                symbol_name,
                SymbolType.IMPORT,
                line_number=node.lineno
            )
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """访问从模块导入"""
        
        module_name = node.module or ""
        
        for alias in node.names:
            # 记录导入
            import_info = ImportInfo(
                module_name=module_name,
                imported_name=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
                column_offset=node.col_offset
            )
            
            self.symbol_table.add_import(import_info)
            
            # 添加到当前作用域
            symbol_name = alias.asname or alias.name
            self.current_scope.add_symbol(
                symbol_name,
                SymbolType.IMPORT,
                line_number=node.lineno
            )
        
        self.generic_visit(node)

class VariableVisitor(BaseVisitor):
    """变量访问者"""
    
    def visit_Name(self, node: ast.Name) -> None:
        """访问名称节点"""
        
        # 记录变量使用
        self._record_variable_use(node.id, node)
        
        # 检查未使用的变量
        self._check_unused_variable(node)
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """访问赋值语句"""
        
        for target in node.targets:
            if isinstance(target, ast.Name):
                # 记录变量定义
                self._record_variable_def(target.id, node)
            
            elif isinstance(target, ast.Tuple):
                # 解包赋值
                for element in target.elts:
                    if isinstance(element, ast.Name):
                        self._record_variable_def(element.id, node)
        
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """访问带类型注解的赋值"""
        
        if isinstance(node.target, ast.Name):
            self._record_variable_def(node.target.id, node)
        
        self.generic_visit(node)
    
    def _record_variable_def(self, var_name: str, node: ast.AST) -> None:
        """记录变量定义"""
        
        self.current_scope.add_symbol(
            var_name,
            SymbolType.VARIABLE,
            line_number=node.lineno,
            node=node
        )
```

## 2. 未使用检测的域跟踪

### 2.1 域系统设计
```python
@dataclass
class Scope:
    """作用域"""
    
    parent: Optional['Scope'] = None
    scope_type: ScopeType = ScopeType.MODULE
    name: str = ""
    
    # 符号表
    symbols: dict[str, SymbolInfo] = field(default_factory=dict)
    
    # 子作用域
    children: list['Scope'] = field(default_factory=list)
    
    def add_symbol(self, name: str, symbol_type: SymbolType, **kwargs) -> None:
        """添加符号到作用域"""
        
        # 检查符号是否已存在
        if name in self.symbols:
            # 更新使用信息
            self.symbols[name].update_usage(**kwargs)
        else:
            # 创建新符号
            self.symbols[name] = SymbolInfo(
                name=name,
                symbol_type=symbol_type,
                **kwargs
            )
    
    def get_symbol(self, name: str) -> Optional[SymbolInfo]:
        """获取符号"""
        
        # 在当前作用域查找
        if name in self.symbols:
            return self.symbols[name]
        
        # 在父作用域查找
        if self.parent:
            return self.parent.get_symbol(name)
        
        return None
    
    def mark_symbol_used(self, name: str, line_number: int) -> bool:
        """标记符号为已使用"""
        
        symbol = self.get_symbol(name)
        if symbol:
            symbol.mark_used(line_number)
            return True
        
        return False
    
    def get_unused_symbols(self) -> list[SymbolInfo]:
        """获取未使用的符号"""
        
        unused = []
        
        for symbol in self.symbols.values():
            if not symbol.is_used and not symbol.is_exempt:
                unused.append(symbol)
        
        return unused
    
    @property
    def full_name(self) -> str:
        """完整作用域名"""
        
        if self.parent:
            parent_name = self.parent.full_name
            if parent_name:
                return f"{parent_name}.{self.name}"
        
        return self.name

class ScopeType(Enum):
    """作用域类型"""
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    COMPREHENSION = "comprehension"
    LAMBDA = "lambda"
```

### 2.2 符号跟踪系统
```python
@dataclass
class SymbolInfo:
    """符号信息"""
    
    name: str
    symbol_type: SymbolType
    line_number: int
    column_offset: int = 0
    
    # 使用信息
    is_used: bool = False
    used_at: list[int] = field(default_factory=list)  # 使用行号列表
    usage_count: int = 0
    
    # 豁免标志（如django约定、公开API等）
    is_exempt: bool = False
    exemption_reason: Optional[str] = None
    
    # AST节点引用
    node: Optional[ast.AST] = None
    
    def mark_used(self, line_number: int) -> None:
        """标记为已使用"""
        
        self.is_used = True
        self.used_at.append(line_number)
        self.usage_count += 1
    
    def update_usage(self, line_number: int = None, **kwargs) -> None:
        """更新使用信息"""
        
        if line_number:
            self.used_at.append(line_number)
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        
        return {
            "name": self.name,
            "type": self.symbol_type.value,
            "line": self.line_number,
            "column": self.column_offset,
            "is_used": self.is_used,
            "usage_count": self.usage_count,
            "used_at": self.used_at,
            "is_exempt": self.is_exempt,
            "exemption_reason": self.exemption_reason
        }

class SymbolType(Enum):
    """符号类型"""
    IMPORT = "import"
    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    PARAMETER = "parameter"
    ATTRIBUTE = "attribute"
```

### 2.3 未使用导入检测
```python
class UnusedImportDetector:
    """未使用导入检测器"""
    
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
    
    def detect(self) -> list[CheckResult]:
        """检测未使用的导入"""
        
        results = []
        
        for import_info in self.symbol_table.imports:
            # 检查导入是否被使用
            symbol = self.symbol_table.get_symbol(import_info.symbol_name)
            
            if not symbol or not symbol.is_used:
                # 创建检查结果
                result = CheckResult(
                    check_type=CheckType.UNUSED_IMPORT,
                    message=f"Unused import '{import_info.display_name}'",
                    line_number=import_info.line_number,
                    column_offset=import_info.column_offset,
                    severity=Severity.WARNING,
                    data={
                        "import_name": import_info.display_name,
                        "module": import_info.module_name,
                        "imported_as": import_info.alias
                    }
                )
                
                results.append(result)
        
        return results
```

## 3. 嵌套深度计算方法

### 3.1 嵌套深度跟踪器
```python
class NestingDepthTracker:
    """嵌套深度跟踪器"""
    
    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.current_depth: int = 0
        self.max_observed_depth: int = 0
        
        # 嵌套上下文栈
        self.context_stack: list[NestingContext] = []
        
        # 深度违规记录
        self.violations: list[NestingViolation] = []
    
    def enter_context(self, node: ast.AST, context_type: NestingContextType) -> None:
        """进入嵌套上下文"""
        
        # 增加深度
        self.current_depth += 1
        
        # 更新最大深度
        self.max_observed_depth = max(self.max_observed_depth, self.current_depth)
        
        # 记录上下文
        context = NestingContext(
            node=node,
            context_type=context_type,
            depth=self.current_depth,
            start_line=node.lineno if hasattr(node, 'lineno') else 0
        )
        
        self.context_stack.append(context)
        
        # 检查深度违规
        if self.current_depth > self.max_depth:
            self._record_violation(context)
    
    def exit_context(self) -> None:
        """退出嵌套上下文"""
        
        if self.context_stack:
            context = self.context_stack.pop()
            context.end_depth = self.current_depth
            
            # 减少深度
            self.current_depth -= 1
    
    def visit_node(self, node: ast.AST) -> None:
        """访问节点，检查嵌套"""
        
        # 检查是否需要进入新上下文
        context_type = self._get_context_type(node)
        
        if context_type:
            self.enter_context(node, context_type)
            
            # 递归访问子节点
            self._visit_children(node)
            
            self.exit_context()
        else:
            # 普通节点，直接访问子节点
            self._visit_children(node)
    
    def _get_context_type(self, node: ast.AST) -> Optional[NestingContextType]:
        """获取节点的嵌套上下文类型"""
        
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return NestingContextType.FUNCTION
        
        elif isinstance(node, (ast.If, ast.IfExp)):
            return NestingContextType.CONDITIONAL
        
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return NestingContextType.LOOP
        
        elif isinstance(node, (ast.Try, ast.With, ast.AsyncWith)):
            return NestingContextType.BLOCK
        
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return NestingContextType.COMPREHENSION
        
        return None
    
    def _record_violation(self, context: NestingContext) -> None:
        """记录嵌套深度违规"""
        
        violation = NestingViolation(
            context=context,
            max_allowed=self.max_depth,
            actual_depth=context.depth,
            message=f"Nesting depth {context.depth} exceeds maximum {self.max_depth}"
        )
        
        self.violations.append(violation)
```

### 3.2 嵌套上下文定义
```python
@dataclass
class NestingContext:
    """嵌套上下文"""
    
    node: ast.AST
    context_type: NestingContextType
    depth: int
    start_line: int
    end_line: Optional[int] = None
    end_depth: Optional[int] = None
    
    @property
    def node_type(self) -> str:
        """节点类型名称"""
        return type(self.node).__name__
    
    @property
    def description(self) -> str:
        """上下文描述"""
        
        base_name = self.context_type.value
        
        if isinstance(self.node, ast.FunctionDef):
            return f"function '{self.node.name}'"
        elif isinstance(self.node, ast.ClassDef):
            return f"class '{self.node.name}'"
        elif isinstance(self.node, ast.If):
            return "if statement"
        elif isinstance(self.node, ast.For):
            return "for loop"
        elif isinstance(self.node, ast.While):
            return "while loop"
        
        return base_name

class NestingContextType(Enum):
    """嵌套上下文类型"""
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    BLOCK = "block"
    COMPREHENSION = "comprehension"
    LAMBDA = "lambda"
```

## 4. 数据类结果模式

### 4.1 检查结果数据类
```python
@dataclass
class CheckResult:
    """检查结果"""
    
    check_type: CheckType
    message: str
    line_number: int
    column_offset: int = 0
    
    # 严重程度
    severity: Severity = Severity.WARNING
    
    # 详细信息
    data: dict = field(default_factory=dict)
    
    # 上下文信息
    context: str = ""
    suggestion: str = ""
    
    # 源码引用
    source_snippet: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        
        return {
            "check_type": self.check_type.value,
            "message": self.message,
            "location": {
                "line": self.line_number,
                "column": self.column_offset
            },
            "severity": self.severity.value,
            "data": self.data,
            "context": self.context,
            "suggestion": self.suggestion,
            "source_snippet": self.source_snippet
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        
        location = f"line {self.line_number}"
        if self.column_offset > 0:
            location += f", column {self.column_offset}"
        
        return f"[{self.severity.value.upper()}] {self.message} ({location})"

@dataclass
class FunctionLengthResult(CheckResult):
    """函数长度检查结果"""
    
    function_name: str = ""
    line_count: int = 0
    max_allowed: int = 50
    
    def __post_init__(self):
        """后初始化"""
        
        if not self.message:
            self.message = (
                f"Function '{self.function_name}' is too long "
                f"({self.line_count} lines, max {self.max_allowed})"
            )
        
        # 更新数据字段
        self.data.update({
            "function_name": self.function_name,
            "line_count": self.line_count,
            "max_allowed": self.max_allowed
        })

@dataclass  
class NestingDepthResult(CheckResult):
    """嵌套深度检查结果"""
    
    context_type: str = ""
    actual_depth: int = 0
    max_allowed: int = 4
    
    def __post_init__(self):
        """后初始化"""
        
        if not self.message:
            self.message = (
                f"Nesting depth {self.actual_depth} exceeds maximum {self.max_allowed} "
                f"in {self.context_type}"
            )
        
        # 更新数据字段
        self.data.update({
            "context_type": self.context_type,
            "actual_depth": self.actual_depth,
            "max_allowed": self.max_allowed
        })
```

### 4.2 检查类型枚举
```python
class CheckType(Enum):
    """检查类型"""
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    FUNCTION_LENGTH = "function_length"
    NESTING_DEPTH = "nesting_depth"
    CODE_STYLE = "code_style"
    SECURITY = "security"
    PERFORMANCE = "performance"

class Severity(Enum):
    """严重程度"""
    INFO = "info"      # 信息
    WARNING = "warning" # 警告
    ERROR = "error"    # 错误
    CRITICAL = "critical" # 严重
```

### 4.3 完整检查报告
```python
@dataclass
class CodeCheckReport:
    """代码检查报告"""
    
    # 基本信息
    filename: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    check_duration: float = 0.0
    
    # 检查结果
    results: list[CheckResult] = field(default_factory=list)
    
    # 统计信息
    stats: Statistics = field(default_factory=Statistics)
    
    # 摘要
    summary: Summary = field(default_factory=Summary)
    
    def add_result(self, result: CheckResult) -> None:
        """添加检查结果"""
        self.results.append(result)
        
        # 更新统计
        self.stats.update_from_result(result)
    
    def get_results_by_type(self, check_type: CheckType) -> list[CheckResult]:
        """按类型获取检查结果"""
        return [r for r in self.results if r.check_type == check_type]
    
    def get_results_by_severity(self, severity: Severity) -> list[CheckResult]:
        """按严重程度获取检查结果"""
        return [r for r in self.results if r.severity == severity]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        
        # 按严重程度分组
        results_by_severity = {
            severity.value: [
                r.to_dict() for r in self.get_results_by_severity(severity)
            ]
            for severity in Severity
        }
        
        # 按检查类型分组
        results_by_type = {
            check_type.value: [
                r.to_dict() for r in self.get_results_by_type(check_type)
            ]
            for check_type in CheckType
        }
        
        return {
            "filename": self.filename,
            "timestamp": self.timestamp.isoformat(),
            "check_duration": self.check_duration,
            "summary": self.summary.to_dict(),
            "statistics": self.stats.to_dict(),
            "results": {
                "by_severity": results_by_severity,
                "by_type": results_by_type,
                "all": [r.to_dict() for r in self.results]
            }
        }
```

## 5. 约束确认

### 约束1: Python 3.10+标准库
- 仅使用Python 3.10+标准库
- 利用ast模块进行代码分析
- 不使用外部依赖

### 约束2: ast模块分析
- 使用ast.NodeVisitor遍历AST
- 使用ast.walk进行全树遍历
- 不使用正则表达式进行代码模式匹配

### 约束3: 数据类包装结果
- 所有检查结果使用dataclass包装
- 提供to_dict()序列化方法
- 结果对象可扩展

### 约束4: 完整类型注解
- 所有公共方法都有类型注解
- 类属性有类型注解
- 返回类型明确指定

### 约束5: 实现四项检查
- 未使用导入检测
- 未使用变量检测
- 函数长度检测（>50行）
- 嵌套深度检测（>4层）

### 约束6: 单文件CodeChecker类
- 所有代码在一个Python文件中
- CodeChecker类作为主要输出
- 包含完整的代码检查逻辑

## 6. 主检查器类

### 6.1 CodeChecker类设计
```python
class CodeChecker:
    """Python代码检查器"""
    
    def __init__(
        self,
        max_function_length: int = 50,
        max_nesting_depth: int = 4,
        check_unused_imports: bool = True,
        check_unused_variables: bool = True,
        check_function_length: bool = True,
        check_nesting_depth: bool = True
    ):
        # 检查配置
        self.config = CheckerConfig(
            max_function_length=max_function_length,
            max_nesting_depth=max_nesting_depth,
            check_unused_imports=check_unused_imports,
            check_unused_variables=check_unused_variables,
            check_function_length=check_function_length,
            check_nesting_depth=check_nesting_depth
        )
        
        # 访问者实例
        self.visitors = self._create_visitors()
        
        # 报告生成器
        self.report_generator = ReportGenerator()
    
    def check(self, source_code: str, filename: str = "<string>") -> CodeCheckReport:
        """检查源代码"""
        
        start_time = time.time()
        
        try:
            # 解析AST
            tree = ast.parse(source_code, filename)
            
            # 运行所有检查
            report = self._run_checks(tree, source_code, filename)
            
            # 计算检查时间
            report.check_duration = time.time() - start_time
            
            return report
            
        except SyntaxError as e:
            # 处理语法错误
            return self._handle_syntax_error(e, filename)
    
    def _run_checks(self, tree: ast.AST, source_code: str, filename: str) -> CodeCheckReport:
        """运行所有检查"""
        
        # 创建报告
        report = CodeCheckReport(filename=filename)
        
        # 运行每个访问者
        for visitor in self.visitors:
            visitor.visit(tree)
            
            # 收集结果
            for result in visitor.results:
                # 添加源码片段
                if hasattr(result, 'line_number'):
                    result.source_snippet = self._extract_source_snippet(
                        source_code, result.line_number
                    )
                
                report.add_result(result)
        
        # 生成摘要
        report.summary = self.report_generator.generate_summary(report)
        
        return report
```

---

*文档字数: 约1998字*