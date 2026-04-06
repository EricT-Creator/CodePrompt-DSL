# MC-PY-01: 基于插件的数据管道技术方案

## 项目概述
本方案设计一个插件化的ETL数据管道系统，支持运行时动态加载插件、条件分支执行和错误隔离。管道将数据流经一系列插件进行转换，每个插件实现统一的转换接口，支持条件执行和容错处理。

## 约束解析
根据Header约束，本方案需满足以下技术要求：

| 约束 | 含义 | 技术实现 |
|------|------|----------|
| `[L]PY310` | Python 3.10+版本 | 使用Python 3.10+语法特性，如match语句、类型联合运算符 |
| `[D]STDLIB_ONLY` | 仅使用Python标准库 | 仅依赖`typing`, `pathlib`, `json`, `os`, `sys`等标准库 |
| `[!D]NO_IMPORTLIB` | 禁止使用importlib | 使用`exec()`动态执行插件代码，而非importlib |
| `[PLUGIN]EXEC` | 使用exec()加载插件 | 通过字符串执行插件的`transform`函数 |
| `[!D]NO_ABC` | 禁止使用抽象基类 | 使用`typing.Protocol`而非`abc.ABC` |
| `[IFACE]PROTOCOL` | 使用Protocol定义接口 | 定义`TransformProtocol`作为插件接口 |
| `[TYPE]FULL_HINTS` | 完整的类型提示 | 所有函数、变量都有详细类型注解 |
| `[ERR]ISOLATE` | 错误隔离机制 | 插件错误不影响管道整体运行 |
| `[O]CLASS` | 使用类实现 | 所有功能封装在类中 |
| `[FILE]SINGLE` | 单文件实现 | 所有代码在一个.py文件中 |

## 架构设计

### 1. 核心类架构

#### DataPipeline类
主类，负责管道的生命周期管理：
- `__init__()`: 初始化管道，设置插件目录、条件字典、错误处理器
- `add_plugin()`: 加载并注册插件
- `run()`: 执行管道，数据流经所有插件
- `_execute_plugin()`: 安全执行单个插件，包含错误隔离

#### Plugin类
插件包装器：
- `name`: 插件名称
- `condition`: 执行条件（可选）
- `transform_func`: 实际的转换函数
- `should_execute()`: 检查是否满足执行条件

### 2. 接口定义

```python
from typing import Protocol, TypeVar, Any, Optional

T = TypeVar('T')

class TransformProtocol(Protocol):
    """插件转换接口"""
    def transform(self, data: T, context: dict[str, Any]) -> T:
        """转换数据，返回处理后的数据"""
        ...
```

### 3. 插件加载机制

#### 动态代码执行流程
1. **读取插件文件**: 从指定目录读取`.py`文件
2. **验证接口**: 检查代码中是否包含`transform`函数
3. **执行环境**: 创建安全执行环境，限制可用模块
4. **函数提取**: 通过`exec()`执行代码，从全局命名空间提取`transform`函数
5. **包装器创建**: 创建`Plugin`实例包装执行函数

#### 条件执行设计
- 每个插件可关联条件表达式
- 条件基于上下文数据评估
- 条件为`None`时始终执行
- 条件格式: `"context['user_type'] == 'premium'"`

### 4. 数据流设计

#### 数据模型
```python
from typing import TypedDict

class PipelineContext(TypedDict, total=False):
    """管道执行上下文"""
    user_type: str  # 用户类型
    data_source: str  # 数据源标识
    timestamp: str  # 时间戳
    # 其他自定义字段
```

#### 执行流程
1. **初始化**: 加载所有插件，解析条件
2. **迭代执行**: 
   - 检查插件执行条件
   - 满足条件则执行转换
   - 不满足条件则跳过
3. **错误处理**: 
   - 捕获插件异常
   - 记录错误信息
   - 继续执行后续插件
4. **结果收集**: 返回最终数据和错误报告

### 5. 错误隔离机制

#### 多层错误防护
1. **语法错误防护**: 在插件加载时检测语法错误
2. **运行时错误防护**: 使用try-except包装每个插件执行
3. **资源释放**: 确保插件异常不影响管道资源
4. **错误报告**: 收集错误信息，生成结构化报告

#### 错误处理器设计
- `ErrorCollector`: 收集所有插件错误
- `ErrorReport`: 生成错误报告，包含插件名、错误类型、堆栈跟踪
- `FallbackHandler`: 提供备选处理逻辑

## 关键实现策略

### 1. exec()安全执行策略
- 限制可访问的全局命名空间
- 禁用危险内置函数（如`open`, `import`）
- 提供安全的执行环境
- 验证执行结果类型

### 2. 条件表达式解析
- 使用Python的`eval()`在受限环境中评估条件
- 提供预定义的安全变量
- 支持常见比较运算符和逻辑运算符

### 3. 类型安全保证
- 使用`typing`模块完整类型提示
- 运行时类型检查（可选）
- 数据验证装饰器

### 4. 性能优化
- 插件预编译和缓存
- 条件预解析
- 批量数据处理的优化

## 约束确认

### Constraint Acknowledgment

1. **`[L]PY310`** ✅
   - 方案使用Python 3.10+的`typing.Protocol`和`TypeVar`语法
   - 可选使用`match`语句进行条件分支
   - 类型提示遵循Python 3.10标准

2. **`[D]STDLIB_ONLY`** ✅
   - 仅使用Python标准库：`typing`, `pathlib`, `os`, `sys`, `json`
   - 不依赖任何第三方库
   - 所有功能基于标准库实现

3. **`[!D]NO_IMPORTLIB`** ✅
   - 完全避免使用`importlib`模块
   - 使用`exec()`动态执行插件代码
   - 通过字符串执行而非模块导入

4. **`[PLUGIN]EXEC`** ✅
   - 核心插件加载机制使用`exec()`函数
   - 在受限环境中执行插件代码字符串
   - 从执行结果中提取转换函数

5. **`[!D]NO_ABC`** ✅
   - 不使用`abc.ABC`或`abstractmethod`
   - 使用`typing.Protocol`定义接口
   - 通过结构性子类型而非继承实现多态

6. **`[IFACE]PROTOCOL`** ✅
   - 定义`TransformProtocol`作为所有插件的接口
   - 使用结构类型检查而非名义类型检查
   - 支持鸭子类型

7. **`[TYPE]FULL_HINTS`** ✅
   - 所有函数参数和返回值都有完整类型注解
   - 使用`TypedDict`定义上下文数据结构
   - 变量声明包含类型提示

8. **`[ERR]ISOLATE`** ✅
   - 每个插件在独立的try-except块中执行
   - 插件错误被捕获并记录，不影响管道继续执行
   - 提供错误报告和恢复机制

9. **`[O]CLASS`** ✅
   - 主要功能封装在`DataPipeline`类中
   - `Plugin`类包装插件实例
   - `ErrorCollector`类管理错误处理

10. **`[FILE]SINGLE`** ✅
   - 所有代码实现在单个`.py`文件中
   - 包含所有类、函数和类型定义
   - 自包含，无需外部模块

## 扩展性与维护性

### 1. 插件生态系统
- 插件可独立开发、测试
- 支持热加载和热替换
- 插件版本管理

### 2. 监控与调试
- 执行日志记录
- 性能指标收集
- 调试模式支持

### 3. 配置管理
- 基于JSON/YAML的管道配置
- 环境变量支持
- 条件表达式配置化

## 总结
本技术方案设计了一个符合所有Header约束的插件化数据管道系统。通过使用Python 3.10+的Protocol接口、exec()动态加载、完整的类型提示和错误隔离机制，实现了灵活、安全、可维护的ETL管道架构。方案严格遵循约束要求，同时提供了良好的扩展性和可维护性。