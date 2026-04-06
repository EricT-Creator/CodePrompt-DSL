# MC-PY-01: 插件式ETL数据管道技术方案

## 1. Pipeline类架构

### 1.1 核心类设计
```python
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from contextlib import contextmanager

@dataclass
class PipelineConfig:
    """管道配置"""
    name: str
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: Optional[float] = None
    enable_conditional_branches: bool = True
    error_isolation: bool = True
    log_level: str = "INFO"

@dataclass
class PipelineContext:
    """管道执行上下文"""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List["PipelineError"] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    current_plugin: Optional[str] = None
    branch_conditions: Dict[str, bool] = field(default_factory=dict)
    
    def add_error(self, error: "PipelineError"):
        """添加错误到上下文"""
        self.errors.append(error)
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """安全获取数据"""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value
    
    def update_metadata(self, **kwargs):
        """更新元数据"""
        self.metadata.update(kwargs)

@dataclass
class PipelineResult:
    """管道执行结果"""
    success: bool
    data: Dict[str, Any]
    errors: List["PipelineError"]
    execution_time: float
    plugins_executed: List[str]
    plugins_skipped: List[str]
    context: PipelineContext
    
    @property
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "execution_time": self.execution_time,
            "plugins_executed": self.plugins_executed,
            "plugins_skipped": self.plugins_skipped,
            "error_count": len(self.errors),
            "data_keys": list(self.data.keys())
        }
```

### 1.2 管道状态机
```python
class PipelineState:
    """管道状态管理"""
    
    STATES = {
        "IDLE": "空闲状态",
        "LOADING_PLUGINS": "加载插件",
        "VALIDATING": "验证插件",
        "EXECUTING": "执行中",
        "PAUSED": "暂停",
        "COMPLETED": "完成",
        "FAILED": "失败",
        "CANCELLED": "取消"
    }
    
    def __init__(self):
        self.current_state = "IDLE"
        self.previous_state = None
        self.state_history: List[Dict[str, Any]] = []
    
    def transition(self, new_state: str, reason: str = ""):
        """状态转换"""
        if new_state not in self.STATES:
            raise ValueError(f"Invalid state: {new_state}")
        
        transition_info = {
            "from": self.current_state,
            "to": new_state,
            "timestamp": datetime.now(),
            "reason": reason
        }
        
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_history.append(transition_info)
        
        return transition_info
    
    def can_transition_to(self, target_state: str) -> bool:
        """检查是否可以转换到目标状态"""
        # 定义状态转换规则
        transitions = {
            "IDLE": ["LOADING_PLUGINS", "CANCELLED"],
            "LOADING_PLUGINS": ["VALIDATING", "FAILED", "CANCELLED"],
            "VALIDATING": ["EXECUTING", "FAILED", "CANCELLED"],
            "EXECUTING": ["PAUSED", "COMPLETED", "FAILED", "CANCELLED"],
            "PAUSED": ["EXECUTING", "CANCELLED"],
            "COMPLETED": ["IDLE"],
            "FAILED": ["IDLE"],
            "CANCELLED": ["IDLE"]
        }
        
        return target_state in transitions.get(self.current_state, [])
```

## 2. 插件加载机制（exec流程）

### 2.1 exec()动态加载
```python
import ast
import sys
from types import ModuleType
from typing import Tuple, Optional

class PluginLoader:
    """插件加载器（使用exec()）"""
    
    def __init__(self):
        self.loaded_plugins: Dict[str, "TransformPlugin"] = {}
        self.plugin_sources: Dict[str, str] = {}
    
    def load_plugin_from_source(self, plugin_name: str, source_code: str) -> "TransformPlugin":
        """
        从源代码加载插件
        
        Args:
            plugin_name: 插件名称
            source_code: 插件源代码
        
        Returns:
            TransformPlugin实例
        
        Raises:
            PluginLoadError: 加载失败
        """
        # 安全性检查：验证源代码
        self._validate_source_code(source_code)
        
        # 创建插件模块命名空间
        plugin_namespace = {
            "__name__": f"plugin_{plugin_name}",
            "TransformPlugin": TransformPlugin,  # 注入基类/协议
            "PipelineContext": PipelineContext,
            "PluginError": PluginError
        }
        
        try:
            # 使用exec()执行源代码
            exec(source_code, plugin_namespace)
        except SyntaxError as e:
            raise PluginLoadError(f"语法错误: {e}")
        except Exception as e:
            raise PluginLoadError(f"执行错误: {e}")
        
        # 查找插件类
        plugin_class = self._find_plugin_class(plugin_namespace, plugin_name)
        if not plugin_class:
            raise PluginLoadError(f"未找到插件类: {plugin_name}")
        
        # 验证插件类
        if not self._validate_plugin_class(plugin_class):
            raise PluginLoadError(f"插件类验证失败: {plugin_name}")
        
        # 创建插件实例
        try:
            plugin_instance = plugin_class()
        except Exception as e:
            raise PluginLoadError(f"插件实例化失败: {e}")
        
        # 存储插件
        self.loaded_plugins[plugin_name] = plugin_instance
        self.plugin_sources[plugin_name] = source_code
        
        return plugin_instance
    
    def _validate_source_code(self, source_code: str):
        """验证源代码安全性"""
        # 解析AST检查危险操作
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            raise PluginLoadError("源代码语法错误")
        
        # 检查禁止的导入
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ["os", "sys", "subprocess"]:
                        raise PluginLoadError(f"禁止导入模块: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module in ["os", "sys", "subprocess"]:
                    raise PluginLoadError(f"禁止从模块导入: {node.module}")
        
        # 检查exec/eval调用
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["exec", "eval", "__import__"]:
                        raise PluginLoadError(f"禁止调用函数: {node.func.id}")
    
    def _find_plugin_class(self, namespace: Dict, plugin_name: str) -> Optional[type]:
        """在命名空间中查找插件类"""
        # 查找实现TransformPlugin协议的类
        for name, obj in namespace.items():
            if (isinstance(obj, type) and 
                issubclass(obj, TransformPlugin) and 
                obj != TransformPlugin):
                return obj
        
        return None
    
    def _validate_plugin_class(self, plugin_class: type) -> bool:
        """验证插件类是否符合协议"""
        try:
            # 检查必需的方法
            required_methods = ["transform", "get_name", "get_description"]
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    return False
            
            # 检查方法签名
            import inspect
            sig = inspect.signature(plugin_class.transform)
            params = list(sig.parameters.keys())
            
            # transform方法应接受context参数
            if len(params) < 1 or params[0] != "context":
                return False
            
            return True
        except Exception:
            return False
```

### 2.2 插件发现和注册
```python
class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self.plugins: Dict[str, "TransformPlugin"] = {}
        self.plugin_categories: Dict[str, List[str]] = {}
        self.plugin_dependencies: Dict[str, List[str]] = {}
    
    def register_plugin(
        self,
        plugin: "TransformPlugin",
        category: str = "default",
        dependencies: Optional[List[str]] = None
    ):
        """注册插件"""
        plugin_name = plugin.get_name()
        
        if plugin_name in self.plugins:
            raise ValueError(f"插件已注册: {plugin_name}")
        
        self.plugins[plugin_name] = plugin
        
        # 添加到类别
        if category not in self.plugin_categories:
            self.plugin_categories[category] = []
        self.plugin_categories[category].append(plugin_name)
        
        # 记录依赖
        self.plugin_dependencies[plugin_name] = dependencies or []
    
    def get_plugin(self, plugin_name: str) -> Optional["TransformPlugin"]:
        """获取插件"""
        return self.plugins.get(plugin_name)
    
    def list_plugins_by_category(self, category: str) -> List[str]:
        """按类别列出插件"""
        return self.plugin_categories.get(category, [])
    
    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """获取插件依赖"""
        return self.plugin_dependencies.get(plugin_name, [])
    
    def validate_dependencies(self, plugin_names: List[str]) -> List[str]:
        """验证插件依赖关系"""
        missing_deps = []
        
        for plugin_name in plugin_names:
            deps = self.get_plugin_dependencies(plugin_name)
            for dep in deps:
                if dep not in plugin_names and dep not in missing_deps:
                    missing_deps.append(dep)
        
        return missing_deps
```

## 3. Protocol接口定义

### 3.1 转换插件协议
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TransformPlugin(Protocol):
    """转换插件协议"""
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        """
        执行数据转换
        
        Args:
            context: 管道执行上下文
        
        Returns:
            更新后的上下文
        
        Raises:
            PluginError: 插件执行错误
        """
        ...
    
    def get_name(self) -> str:
        """获取插件名称"""
        ...
    
    def get_description(self) -> str:
        """获取插件描述"""
        ...
    
    def get_version(self) -> str:
        """获取插件版本"""
        ...
    
    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """获取配置模式（可选）"""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置（可选）"""
        ...
    
    def cleanup(self):
        """清理资源（可选）"""
        ...
```

### 3.2 插件基类实现
```python
class BaseTransformPlugin:
    """转换插件基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if hasattr(self, "get_config_schema"):
            schema = self.get_config_schema()
            if schema and not self.validate_config(self.config):
                raise PluginError(f"配置验证失败: {self.get_name()}")
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        """执行转换（由子类实现）"""
        raise NotImplementedError("子类必须实现transform方法")
    
    def get_name(self) -> str:
        """获取插件名称（由子类实现）"""
        raise NotImplementedError("子类必须实现get_name方法")
    
    def get_description(self) -> str:
        """获取插件描述"""
        return "No description provided"
    
    def get_version(self) -> str:
        """获取插件版本"""
        return "1.0.0"
    
    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """获取配置模式"""
        return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        return True
    
    def cleanup(self):
        """清理资源"""
        pass
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.get_name()} (v{self.get_version()})"
```

### 3.3 示例插件实现
```python
class CSVReaderPlugin(BaseTransformPlugin):
    """CSV读取插件"""
    
    def get_name(self) -> str:
        return "csv_reader"
    
    def get_description(self) -> str:
        return "读取CSV文件并转换为字典列表"
    
    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "file_path": {"type": "string", "required": True},
            "delimiter": {"type": "string", "default": ","},
            "encoding": {"type": "string", "default": "utf-8"}
        }
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        import csv
        
        file_path = self.config.get("file_path")
        delimiter = self.config.get("delimiter", ",")
        encoding = self.config.get("encoding", "utf-8")
        
        if not file_path:
            raise PluginError("file_path配置缺失")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                data = list(reader)
            
            context.set_data("csv_data", data)
            context.update_metadata(
                csv_file=file_path,
                row_count=len(data),
                columns=list(data[0].keys()) if data else []
            )
            
            return context
        except FileNotFoundError:
            raise PluginError(f"文件不存在: {file_path}")
        except Exception as e:
            raise PluginError(f"读取CSV失败: {e}")
```

## 4. 条件分支设计

### 4.1 条件表达式解析
```python
class ConditionParser:
    """条件表达式解析器"""
    
    def __init__(self):
        self.operators = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "in": lambda a, b: a in b,
            "not in": lambda a, b: a not in b,
            "and": lambda a, b: a and b,
            "or": lambda a, b: a or b,
            "not": lambda a: not a
        }
    
    def parse_condition(self, condition_str: str, context: PipelineContext) -> bool:
        """
        解析条件表达式
        
        支持格式:
        - "data.key == 'value'"
        - "len(data.list) > 10"
        - "metadata.status in ['success', 'pending']"
        - "data.count > 5 and data.type == 'user'"
        """
        try:
            # 提取变量引用
            condition = self._replace_variables(condition_str, context)
            
            # 安全评估表达式
            return self._safe_eval(condition)
        except Exception as e:
            raise ConditionError(f"条件解析失败: {condition_str}, 错误: {e}")
    
    def _replace_variables(self, condition: str, context: PipelineContext) -> str:
        """替换变量引用"""
        import re
        
        # 匹配 data.key 或 metadata.key 格式
        pattern = r'(data|metadata)\.(\w+)'
        
        def replace_match(match):
            var_type = match.group(1)  # data 或 metadata
            var_name = match.group(2)  # 变量名
            
            if var_type == "data":
                value = context.get_data(var_name)
            else:  # metadata
                value = context.metadata.get(var_name)
            
            # 转换为Python字面量
            return self._value_to_literal(value)
        
        return re.sub(pattern, replace_match, condition)
    
    def _value_to_literal(self, value: Any) -> str:
        """将值转换为Python字面量"""
        if value is None:
            return "None"
        elif isinstance(value, bool):
            return "True" if value else "False"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return repr(value)
        elif isinstance(value, (list, tuple)):
            items = [self._value_to_literal(item) for item in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            items = [f"{self._value_to_literal(k)}: {self._value_to_literal(v)}" 
                    for k, v in value.items()]
            return f"{{{', '.join(items)}}}"
        else:
            # 复杂对象转换为字符串表示
            return repr(str(value))
    
    def _safe_eval(self, expression: str) -> bool:
        """安全评估表达式"""
        # 限制可用的内置函数
        safe_builtins = {
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set
        }
        
        # 创建安全命名空间
        namespace = {
            '__builtins__': safe_builtins,
            **self.operators
        }
        
        try:
            result = eval(expression, namespace)
            return bool(result)
        except Exception as e:
            raise ConditionError(f"表达式评估失败: {expression}, 错误: {e}")
```

### 4.2 分支执行器
```python
class BranchExecutor:
    """分支执行器"""
    
    def __init__(self, condition_parser: ConditionParser):
        self.condition_parser = condition_parser
        self.branches: List["PipelineBranch"] = []
    
    def add_branch(
        self,
        branch_name: str,
        condition: str,
        plugins: List[str],
        else_plugins: Optional[List[str]] = None
    ):
        """添加分支"""
        branch = PipelineBranch(
            name=branch_name,
            condition=condition,
            plugins=plugins,
            else_plugins=else_plugins or []
        )
        self.branches.append(branch)
    
    async def execute_branches(
        self,
        context: PipelineContext,
        plugin_registry: PluginRegistry,
        pipeline: "DataPipeline"
    ) -> PipelineContext:
        """执行所有分支"""
        for branch in self.branches:
            context = await self._execute_branch(branch, context, plugin_registry, pipeline)
        
        return context
    
    async def _execute_branch(
        self,
        branch: "PipelineBranch",
        context: PipelineContext,
        plugin_registry: PluginRegistry,
        pipeline: "DataPipeline"
    ) -> PipelineContext:
        """执行单个分支"""
        try:
            # 评估条件
            condition_result = self.condition_parser.parse_condition(
                branch.condition, context
            )
            
            # 记录条件结果
            context.branch_conditions[branch.name] = condition_result
            
            # 选择要执行的插件
            plugins_to_execute = (
                branch.plugins if condition_result 
                else branch.else_plugins
            )
            
            # 执行选中的插件
            if plugins_to_execute:
                context = await pipeline._execute_plugin_sequence(
                    plugins_to_execute, 
                    context, 
                    plugin_registry,
                    branch_prefix=f"[{branch.name}] "
                )
        
        except ConditionError as e:
            # 条件解析错误，跳过此分支
            context.add_error(PipelineError(
                plugin_name=branch.name,
                error_type="condition_error",
                message=str(e),
                recoverable=True
            ))
        
        return context
```

## 5. 约束确认

### 5.1 Python 3.10+, stdlib only
- 要求Python 3.10或更高版本
- 仅使用标准库
- 不引入外部依赖

### 5.2 exec() for plugin loading, no importlib
- 使用exec()动态加载插件
- 不使用importlib或import语句
- 手动管理插件命名空间

### 5.3 Protocol for interfaces, no ABC
- 使用typing.Protocol定义接口
- 不使用ABC抽象基类
- 运行时协议检查

### 5.4 Full type annotations
- 完整的类型注解
- 使用mypy兼容的类型提示
- 类型安全的API设计

### 5.5 Plugin errors isolated
- 插件错误隔离
- 一个插件失败不影响其他插件
- 可恢复的错误处理

### 5.6 Single file, class output
- 所有代码在单个Python文件中
- 输出为类定义
- 自包含实现