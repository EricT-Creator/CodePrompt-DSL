# MC-PY-04: AST代码检查器技术方案

## 项目概述
本方案设计一个基于AST的Python代码检查器，使用AST Visitor模式遍历语法树，检测代码质量问题。检查器支持四种检查：未使用的导入、未使用的变量、函数过长（>50行）和嵌套过深（>4层）。结果使用dataclass表示，提供详细的检查报告。

## 约束解析
根据Header约束，本方案需满足以下技术要求：

| 约束 | 含义 | 技术实现 |
|------|------|----------|
| `[L]PY310` | Python 3.10+版本 | 使用Python 3.10+语法特性，如match语句、类型参数 |
| `[D]STDLIB_ONLY` | 仅使用Python标准库 | 仅依赖`ast`, `typing`, `dataclasses`等标准库 |
| `[MUST]AST_VISITOR` | 必须使用AST Visitor模式 | 继承`ast.NodeVisitor`，实现visit方法 |
| `[!D]NO_REGEX` | 禁止使用正则表达式 | 完全不使用`re`模块，纯AST分析 |
| `[O]DATACLASS` | 使用dataclass表示结果 | 使用`@dataclass`定义检查结果数据结构 |
| `[TYPE]FULL_HINTS` | 完整的类型提示 | 所有函数、变量都有详细类型注解 |
| `[CHECK]IMPORT+VAR+LEN+NEST` | 检查四种问题 | 检查未使用的导入、未使用的变量、函数过长、嵌套过深 |
| `[O]CLASS` | 使用类实现 | 所有功能封装在类中 |
| `[FILE]SINGLE` | 单文件实现 | 所有代码在一个.py文件中 |

## 架构设计

### 1. 核心类架构

#### CodeChecker类
主类，负责代码检查和结果聚合：
- `__init__()`: 初始化检查器，设置检查配置
- `check()`: 检查代码字符串，返回检查结果
- `check_file()`: 检查文件，返回检查结果

#### ASTVisitor类
AST遍历器，继承`ast.NodeVisitor`：
- `visit_Import()`: 处理import语句
- `visit_ImportFrom()`: 处理from ... import语句
- `visit_FunctionDef()`: 处理函数定义
- `visit_Name()`: 处理变量名
- `visit_If()` / `visit_For()` / `visit_While()`: 处理嵌套结构

#### ScopeTracker类
作用域跟踪器：
- `enter_scope()`: 进入新作用域
- `exit_scope()`: 退出作用域
- `add_variable()`: 记录变量定义
- `mark_variable_used()`: 标记变量使用
- `get_unused_variables()`: 获取未使用变量

### 2. 数据结构设计

#### 检查结果dataclass
```python
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class CheckResult:
    """检查结果基类"""
    line: int  # 行号
    col: int   # 列号
    message: str  # 错误消息

@dataclass
class UnusedImportResult(CheckResult):
    """未使用的导入"""
    module: str  # 模块名
    names: List[str]  # 未使用的名称列表

@dataclass
class UnusedVariableResult(CheckResult):
    """未使用的变量"""
    variable_name: str  # 变量名
    scope_type: str  # 作用域类型（function/class/module）

@dataclass
class LongFunctionResult(CheckResult):
    """函数过长"""
    function_name: str  # 函数名
    line_count: int  # 行数
    limit: int = 50  # 限制行数

@dataclass
class DeepNestingResult(CheckResult):
    """嵌套过深"""
    node_type: str  # 节点类型（if/for/while/try）
    nesting_depth: int  # 嵌套深度
    limit: int = 4  # 限制深度

@dataclass
class CheckReport:
    """完整的检查报告"""
    unused_imports: List[UnusedImportResult] = field(default_factory=list)
    unused_variables: List[UnusedVariableResult] = field(default_factory=list)
    long_functions: List[LongFunctionResult] = field(default_factory=list)
    deep_nesting: List[DeepNestingResult] = field(default_factory=list)
    total_issues: int = 0
    
    def __post_init__(self):
        self.total_issues = (
            len(self.unused_imports) +
            len(self.unused_variables) +
            len(self.long_functions) +
            len(self.deep_nesting)
        )
```

### 3. 检查算法设计

#### 未使用的导入检查
**算法步骤**：
1. 记录所有导入的模块和名称
2. 跟踪所有使用的名称
3. 比较导入名称和使用名称
4. 报告未使用的导入

**实现细节**：
- 处理`import module`语句
- 处理`from module import name1, name2`语句
- 支持别名（`import module as alias`）
- 考虑星号导入（`from module import *`）

#### 未使用的变量检查
**作用域模型**：
- 模块作用域（全局）
- 类作用域
- 函数作用域
- 闭包作用域

**算法步骤**：
1. 进入作用域时创建新的变量表
2. 记录变量定义（赋值、参数、循环变量）
3. 标记变量使用（读取、调用）
4. 退出作用域时检查未使用变量

#### 函数长度检查
**行数计算**：
1. 获取函数节点的起始行和结束行
2. 计算行数差
3. 考虑空行和注释（可选）
4. 超过阈值时报告

**实现细节**：
- 使用`node.lineno`和`node.end_lineno`
- 支持装饰器函数
- 处理嵌套函数

#### 嵌套深度检查
**嵌套跟踪**：
1. 维护嵌套深度计数器
2. 进入嵌套结构（if/for/while/try/with）时递增
3. 退出时递减
4. 超过阈值时报告

**嵌套结构类型**：
- 条件语句（if/elif/else）
- 循环语句（for/while）
- 异常处理（try/except/finally）
- 上下文管理器（with）

### 4. AST Visitor设计

#### Visitor类层次结构
```python
class BaseVisitor(ast.NodeVisitor):
    """基础Visitor，提供作用域支持"""
    def __init__(self):
        self.scope_tracker = ScopeTracker()
        self.current_function = None
        self.nesting_depth = 0

class ImportVisitor(BaseVisitor):
    """导入检查Visitor"""
    def __init__(self):
        super().__init__()
        self.imports = {}  # 导入映射
        self.used_names = set()  # 已使用名称
        
    def visit_Import(self, node):
        # 处理import语句
        for alias in node.names:
            self.imports[alias.name] = {
                'lineno': node.lineno,
                'col': node.col_offset,
                'asname': alias.asname
            }
        self.generic_visit(node)
    
    def visit_Name(self, node):
        # 记录名称使用
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)
```

#### 多Visitor协调
使用`ast.NodeTransformer`或组合多个Visitor：

**策略1：组合Visitor**
```python
class CompositeVisitor(ast.NodeVisitor):
    """组合多个Visitor"""
    def __init__(self):
        self.visitors = [
            ImportVisitor(),
            VariableVisitor(),
            FunctionVisitor(),
            NestingVisitor()
        ]
    
    def visit(self, node):
        for visitor in self.visitors:
            visitor.visit(node)
```

**策略2：单次遍历收集**
```python
class AllInOneVisitor(ast.NodeVisitor):
    """单Visitor处理所有检查"""
    def __init__(self):
        self.imports = {}
        self.used_names = set()
        self.variable_defs = {}
        self.current_function = None
        self.nesting_depth = 0
        self.results = CheckReport()
```

## 关键实现策略

### 1. 作用域精确跟踪
- 区分不同作用域类型
- 处理闭包和嵌套作用域
- 正确处理全局和非局部声明

### 2. 名称解析
- 处理属性访问（obj.attr）
- 处理下标访问（list[index]）
- 处理函数调用

### 3. 行号精确计算
- 使用AST节点的`lineno`和`end_lineno`
- 考虑多行语句
- 处理续行符

### 4. 性能优化
- 单次AST遍历完成所有检查
- 使用缓存避免重复计算
- 惰性求值

## 约束确认

### Constraint Acknowledgment

1. **`[L]PY310`** ✅
   - 方案使用Python 3.10+的`ast`模块特性
   - 使用`match`语句处理节点类型
   - 使用类型参数和泛型

2. **`[D]STDLIB_ONLY`** ✅
   - 仅使用Python标准库：`ast`, `typing`, `dataclasses`
   - 不依赖任何第三方库
   - 所有功能基于标准库实现

3. **`[MUST]AST_VISITOR`** ✅
   - 继承`ast.NodeVisitor`基类
   - 实现所有必要的visit方法
   - 使用Visitor模式遍历AST

4. **`[!D]NO_REGEX`** ✅
   - 完全不使用`re`模块
   - 纯AST分析，不依赖正则表达式
   - 所有检查基于语法树节点

5. **`[O]DATACLASS`** ✅
   - 使用`@dataclass`装饰器定义所有结果类
   - 自动生成`__init__`, `__repr__`等方法
   - 支持字段默认值和类型提示

6. **`[TYPE]FULL_HINTS`** ✅
   - 所有函数参数和返回值都有完整类型注解
   - 使用`TypeVar`和泛型
   - 变量声明包含类型提示

7. **`[CHECK]IMPORT+VAR+LEN+NEST`** ✅
   - 实现未使用的导入检查
   - 实现未使用的变量检查
   - 实现函数长度检查（>50行）
   - 实现嵌套深度检查（>4层）

8. **`[O]CLASS`** ✅
   - 主要功能封装在`CodeChecker`类中
   - `ASTVisitor`类处理AST遍历
   - `ScopeTracker`类管理作用域
   - 所有检查作为类方法实现

9. **`[FILE]SINGLE`** ✅
   - 所有代码实现在单个`.py`文件中
   - 包含所有类、函数和类型定义
   - 自包含，无需外部模块

## 高级功能

### 1. 配置系统
- 可配置的检查阈值
- 启用/禁用特定检查
- 自定义检查规则

### 2. 错误恢复
- 语法错误时的优雅处理
- 部分AST解析
- 错误位置精确定位

### 3. 报告生成
- 多种输出格式（JSON、Markdown、HTML）
- 统计信息汇总
- 严重程度分级

### 4. 增量检查
- 基于文件修改时间缓存
- 增量AST解析
- 差异报告

## 性能优化

### 1. AST缓存
- 基于文件内容哈希缓存AST
- 缓存检查结果
- 智能缓存失效

### 2. 并行处理
- 多文件并行检查
- 线程池执行
- 结果聚合

### 3. 内存优化
- 流式AST处理
- 延迟加载大文件
- 内存使用监控

## 使用示例

### 基本使用
```python
checker = CodeChecker()

# 检查代码字符串
code = """
import os
import sys
from typing import List

def long_function():
    x = 1
    y = 2  # 未使用
    if x > 0:
        if True:
            if False:
                if 1 == 1:
                    print("deep nesting")
    return x

result = checker.check(code)
print(f"发现 {result.total_issues} 个问题")

# 输出结果
for issue in result.unused_imports:
    print(f"未使用的导入: {issue.module} 在第 {issue.line} 行")
```

### 配置文件
```python
config = {
    'max_function_length': 50,
    'max_nesting_depth': 4,
    'check_unused_imports': True,
    'check_unused_variables': True,
    'check_function_length': True,
    'check_nesting_depth': True,
    'ignore_imports': ['typing'],  # 忽略typing模块
    'ignore_variables': ['_'],  # 忽略单下划线变量
}

checker = CodeChecker(config=config)
```

## 扩展性设计

### 1. 插件系统
- 自定义检查规则
- 第三方插件支持
- 插件发现机制

### 2. 规则引擎
- 基于规则的检查配置
- 规则优先级
- 规则冲突解决

### 3. 集成支持
- 编辑器集成（VSCode、PyCharm）
- CI/CD流水线集成
- 版本控制钩子

## 总结
本技术方案设计了一个符合所有Header约束的AST代码检查器。通过使用AST Visitor模式、dataclass结果表示和完整的类型系统，实现了精确、高效的代码质量检查。方案严格遵循约束要求，同时提供了良好的扩展性、配置性和性能表现。检查器能够帮助开发者发现代码中的常见问题，提高代码质量和可维护性。