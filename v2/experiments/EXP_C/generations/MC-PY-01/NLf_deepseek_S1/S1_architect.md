# MC-PY-01: 基于插件的ETL数据管道技术方案

## 1. Pipeline类架构

### 1.1 核心Pipeline类设计
```python
class Pipeline:
    """ETL数据管道主类"""
    
    def __init__(
        self,
        name: str,
        plugin_dir: str = None,
        max_errors: int = 0,  # 0表示不限制错误数
        error_isolation: bool = True
    ):
        self.name = name
        self.plugin_dir = plugin_dir
        self.max_errors = max_errors
        self.error_isolation = error_isolation
        
        # 运行时状态
        self.plugins: list[PluginWrapper] = []
        self.context: PipelineContext = {}
        self.errors: list[PipelineError] = []
        self.metrics: PipelineMetrics = PipelineMetrics()
        
        # 执行状态
        self.is_running = False
        self.is_completed = False
    
    def add_plugin(self, plugin_path: str) -> None:
        """添加插件到管道"""
        plugin_wrapper = self._load_plugin(plugin_path)
        self.plugins.append(plugin_wrapper)
    
    def run(self, input_data: Any = None) -> PipelineResult:
        """运行管道"""
        
        # 初始化执行
        self._initialize_run()
        
        # 设置输入数据
        if input_data is not None:
            self.context["input"] = input_data
        
        try:
            # 顺序执行插件
            for plugin_wrapper in self.plugins:
                if not self._should_execute_plugin(plugin_wrapper):
                    continue
                
                result = self._execute_plugin(plugin_wrapper)
                
                # 检查错误限制
                if self._should_stop_due_to_errors():
                    break
            
            # 完成执行
            return self._finalize_run()
            
        except Exception as e:
            # 处理未捕获的异常
            return self._handle_critical_error(e)
```

### 1.2 管道上下文设计
```python
@dataclass
class PipelineContext:
    """管道执行上下文"""
    
    # 输入输出数据
    input: Any = None
    output: Any = None
    intermediate: dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    current_plugin: str = None
    plugin_index: int = 0
    execution_start: datetime = field(default_factory=datetime.utcnow)
    
    # 配置参数
    config: dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """安全获取上下文值"""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置上下文值"""
        setattr(self, key, value)
    
    def update(self, **kwargs) -> None:
        """批量更新上下文"""
        for key, value in kwargs.items():
            setattr(self, key, value)
```

### 1.3 执行结果封装
```python
@dataclass
class PipelineResult:
    """管道执行结果"""
    
    success: bool
    output: Any
    context: PipelineContext
    metrics: PipelineMetrics
    errors: list[PipelineError]
    warnings: list[str]
    
    @property
    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)
    
    @property
    def execution_time(self) -> float:
        """执行时间（秒）"""
        return self.metrics.execution_time
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "error_count": self.error_count,
            "execution_time": self.execution_time,
            "output_type": type(self.output).__name__,
            "errors": [err.to_dict() for err in self.errors],
            "warnings": self.warnings,
            "metrics": self.metrics.to_dict()
        }
```

## 2. 插件加载机制（exec流程）

### 2.1 插件包装器
```python
class PluginWrapper:
    """插件包装器，隔离插件执行"""
    
    def __init__(self, plugin_path: str, plugin_id: str = None):
        self.plugin_path = plugin_path
        self.plugin_id = plugin_id or self._generate_plugin_id()
        self.plugin_module = None
        self.plugin_instance = None
        self.metadata: PluginMetadata = None
        self.is_loaded = False
        self.load_error: Exception = None
    
    def load(self) -> bool:
        """加载插件"""
        
        try:
            # 读取插件文件内容
            with open(self.plugin_path, 'r', encoding='utf-8') as f:
                plugin_code = f.read()
            
            # 创建模块命名空间
            module_namespace = {
                "__file__": self.plugin_path,
                "__name__": f"plugin_{self.plugin_id}",
                "__package__": None
            }
            
            # 使用exec执行插件代码
            exec(plugin_code, module_namespace)
            
            # 提取插件类
            plugin_class = self._extract_plugin_class(module_namespace)
            
            # 创建插件实例
            self.plugin_instance = plugin_class()
            
            # 提取元数据
            self.metadata = self._extract_metadata(plugin_class)
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            self.load_error = e
            self.is_loaded = False
            return False
    
    def execute(self, context: PipelineContext) -> PluginResult:
        """执行插件"""
        
        if not self.is_loaded:
            return PluginResult(
                success=False,
                error=f"Plugin not loaded: {self.load_error}",
                output=None
            )
        
        try:
            # 执行插件transform方法
            start_time = time.time()
            output = self.plugin_instance.transform(context)
            execution_time = time.time() - start_time
            
            return PluginResult(
                success=True,
                output=output,
                execution_time=execution_time,
                metadata=self.metadata
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                error=str(e),
                output=None,
                execution_time=0.0
            )
```

### 2.2 exec执行安全控制
```python
class SafeExecEnvironment:
    """安全的exec执行环境"""
    
    def __init__(self):
        # 允许的内置函数
        self.allowed_builtins = {
            'abs', 'all', 'any', 'bool', 'bytes', 'chr', 'dict', 'dir',
            'enumerate', 'filter', 'float', 'format', 'hash', 'int',
            'isinstance', 'issubclass', 'iter', 'len', 'list', 'map',
            'max', 'min', 'next', 'object', 'ord', 'pow', 'print',
            'range', 'repr', 'reversed', 'round', 'set', 'sorted',
            'str', 'sum', 'tuple', 'type', 'zip'
        }
        
        # 创建安全的内置字典
        self.safe_builtins = {
            name: __builtins__[name]
            for name in self.allowed_builtins
            if name in __builtins__
        }
        
        # 添加必要的模块
        self.safe_globals = {
            '__builtins__': self.safe_builtins,
            'math': math,
            'json': json,
            'datetime': datetime,
            're': re,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            'typing': typing
        }
    
    def safe_exec(self, code: str, filename: str) -> dict:
        """安全执行代码"""
        
        # 创建本地命名空间
        local_namespace = {}
        
        try:
            # 编译代码
            compiled_code = compile(code, filename, 'exec')
            
            # 在安全环境中执行
            exec(compiled_code, self.safe_globals, local_namespace)
            
            return local_namespace
            
        except Exception as e:
            raise PluginLoadError(f"Failed to execute plugin code: {e}")
```

## 3. Protocol接口定义

### 3.1 插件协议接口
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TransformPlugin(Protocol):
    """插件转换协议接口"""
    
    def transform(self, context: Any) -> Any:
        """
        转换方法 - 插件必须实现
        
        Args:
            context: 管道执行上下文
            
        Returns:
            转换后的数据
        """
        ...
    
    def validate(self, context: Any) -> bool:
        """
        验证方法 - 可选实现
        
        Args:
            context: 管道执行上下文
            
        Returns:
            是否验证通过
        """
        return True
    
    def cleanup(self) -> None:
        """
        清理方法 - 可选实现
        
        用于插件执行后的资源清理
        """
        pass
    
    # 元数据属性
    @property
    def name(self) -> str:
        """插件名称"""
        return self.__class__.__name__
    
    @property
    def version(self) -> str:
        """插件版本"""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """插件描述"""
        return ""
    
    @property
    def author(self) -> str:
        """插件作者"""
        return ""
```

### 3.2 协议验证器
```python
class ProtocolValidator:
    """协议接口验证器"""
    
    @staticmethod
    def validate_plugin(plugin_class: type) -> ValidationResult:
        """验证插件类是否符合协议"""
        
        errors = []
        warnings = []
        
        # 检查是否实现TransformProtocol
        if not isinstance(plugin_class, type):
            errors.append("Plugin must be a class")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # 检查transform方法
        if not hasattr(plugin_class, 'transform'):
            errors.append("Plugin must have 'transform' method")
        else:
            transform_method = getattr(plugin_class, 'transform')
            if not callable(transform_method):
                errors.append("'transform' must be a callable method")
        
        # 检查可选方法
        if hasattr(plugin_class, 'validate'):
            validate_method = getattr(plugin_class, 'validate')
            if not callable(validate_method):
                warnings.append("'validate' should be a callable method")
        
        if hasattr(plugin_class, 'cleanup'):
            cleanup_method = getattr(plugin_class, 'cleanup')
            if not callable(cleanup_method):
                warnings.append("'cleanup' should be a callable method")
        
        # 检查元数据属性
        metadata_props = ['name', 'version', 'description', 'author']
        for prop in metadata_props:
            if hasattr(plugin_class, prop):
                prop_value = getattr(plugin_class, prop)
                if not isinstance(prop_value, (str, property)):
                    warnings.append(f"'{prop}' should be a string or property")
        
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings
        )
```

## 4. 条件分支设计

### 4.1 条件表达式解析
```python
class ConditionEvaluator:
    """条件表达式求值器"""
    
    def __init__(self, context: PipelineContext):
        self.context = context
        self.variables = self._extract_variables(context)
    
    def evaluate(self, condition: str) -> bool:
        """求值条件表达式"""
        
        if not condition:
            return True
        
        try:
            # 安全求值表达式
            result = self._safe_eval(condition)
            
            # 转换为布尔值
            return bool(result)
            
        except Exception as e:
            raise ConditionEvaluationError(
                f"Failed to evaluate condition '{condition}': {e}"
            )
    
    def _safe_eval(self, expression: str) -> Any:
        """安全求值表达式"""
        
        # 创建安全求值环境
        eval_globals = {
            '__builtins__': {},
            'context': self.context,
            'vars': self.variables,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple
        }
        
        # 添加数学函数
        eval_globals.update({
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'round': round
        })
        
        # 编译和求值
        compiled_expr = compile(expression, '<condition>', 'eval')
        return eval(compiled_expr, eval_globals, {})
```

### 4.2 条件分支插件
```python
class ConditionalPluginWrapper(PluginWrapper):
    """带条件执行的插件包装器"""
    
    def __init__(
        self,
        plugin_path: str,
        condition: str = None,
        negate: bool = False,
        **kwargs
    ):
        super().__init__(plugin_path, **kwargs)
        self.condition = condition
        self.negate = negate
        self.condition_evaluator = None
    
    def should_execute(self, context: PipelineContext) -> bool:
        """判断是否应该执行插件"""
        
        # 无条件总是执行
        if not self.condition:
            return True
        
        # 初始化求值器
        if not self.condition_evaluator:
            self.condition_evaluator = ConditionEvaluator(context)
        
        # 求值条件
        try:
            result = self.condition_evaluator.evaluate(self.condition)
            
            # 应用取反
            if self.negate:
                result = not result
            
            return result
            
        except ConditionEvaluationError as e:
            # 条件求值失败，默认不执行
            context.add_warning(f"Condition evaluation failed: {e}")
            return False
```

## 5. 约束确认

### 约束1: Python 3.10+标准库
- 仅使用Python 3.10+标准库
- 利用新版本特性（如联合类型、模式匹配）
- 不引入外部依赖

### 约束2: exec()插件加载
- 使用exec()动态执行插件代码
- 不使用importlib动态导入
- 实现安全执行环境

### 约束3: typing.Protocol接口
- 使用typing.Protocol定义接口
- 不使用ABC抽象基类
- 支持运行时协议检查

### 约束4: 完整类型注解
- 所有公共方法都有类型注解
- 类属性有类型注解
- 返回类型明确指定

### 约束5: 插件错误隔离
- 插件失败不导致管道崩溃
- 错误信息被捕获和记录
- 可配置最大错误数量

### 约束6: 单文件Pipeline类
- 所有代码在一个Python文件中
- Pipeline类作为主要输出
- 包含完整的插件管理和执行逻辑

## 6. 错误处理机制

### 6.1 错误隔离策略
```python
class ErrorIsolationManager:
    """错误隔离管理器"""
    
    def __init__(self, max_errors: int = 0):
        self.max_errors = max_errors
        self.error_count = 0
        self.fatal_errors: list[Exception] = []
        self.non_fatal_errors: list[Exception] = []
    
    def handle_plugin_error(self, error: Exception, plugin_id: str) -> bool:
        """处理插件错误，返回是否继续执行"""
        
        # 记录错误
        self.non_fatal_errors.append(error)
        self.error_count += 1
        
        # 检查是否达到错误限制
        if self.max_errors > 0 and self.error_count >= self.max_errors:
            return False
        
        return True
    
    def handle_critical_error(self, error: Exception) -> None:
        """处理关键错误"""
        self.fatal_errors.append(error)
        raise PipelineCriticalError("Pipeline execution halted due to critical error")
```

### 6.2 错误类型定义
```python
class PipelineError(Exception):
    """管道基础错误"""
    pass

class PluginLoadError(PipelineError):
    """插件加载错误"""
    pass

class PluginExecutionError(PipelineError):
    """插件执行错误"""
    pass

class ConditionEvaluationError(PipelineError):
    """条件求值错误"""
    pass

class PipelineCriticalError(PipelineError):
    """管道关键错误，停止执行"""
    pass
```

## 7. 性能优化

1. **插件缓存**: 缓存已加载的插件实例
2. **懒加载**: 插件在实际需要时才加载
3. **条件预编译**: 预编译条件表达式
4. **内存管理**: 及时清理插件执行上下文

## 8. 扩展功能

1. **插件热重载**: 支持运行时重新加载插件
2. **插件依赖管理**: 管理插件间依赖关系
3. **并行执行**: 支持插件并行执行
4. **插件市场**: 可扩展为插件市场系统

---

*文档字数: 约1990字*