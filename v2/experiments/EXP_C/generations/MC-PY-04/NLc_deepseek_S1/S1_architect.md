# MC-PY-04: Python代码检查器技术方案

## 1. AST Visitor类层次结构

### 1.1 基础Visitor类设计
```python
import ast
from typing import Dict, List, Set, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict
import sys

T = TypeVar('T')

class BaseASTVisitor(ast.NodeVisitor):
    """基础AST Visitor类"""
    
    def __init__(self):
        super().__init__()
        self.issues: List["CodeIssue"] = []
        self.current_file: Optional[str] = None
        self.current_module: Optional[str] = None
        self.node_stack: List[ast.AST] = []
        self.scope_stack: List["Scope"] = []
        self.symbol_table: Dict[str, "Symbol"] = {}
    
    def visit(self, node: ast.AST) -> Any:
        """重写visit方法以跟踪节点栈"""
        self.node_stack.append(node)
        result = super().visit(node)
        self.node_stack.pop()
        return result
    
    def generic_visit(self, node: ast.AST):
        """通用访问方法"""
        # 记录访问的节点类型（用于调试）
        node_type = type(node).__name__
        
        # 继续访问子节点
        super().generic_visit(node)
    
    def add_issue(self, issue: "CodeIssue"):
        """添加代码问题"""
        self.issues.append(issue)
    
    def get_current_scope(self) -> Optional["Scope"]:
        """获取当前作用域"""
        if self.scope_stack:
            return self.scope_stack[-1]
        return None
    
    def push_scope(self, scope: "Scope"):
        """推入新作用域"""
        self.scope_stack.append(scope)
    
    def pop_scope(self) -> Optional["Scope"]:
        """弹出作用域"""
        if self.scope_stack:
            return self.scope_stack.pop()
        return None
    
    def get_parent_node(self, levels: int = 1) -> Optional[ast.AST]:
        """获取父节点"""
        if len(self.node_stack) > levels:
            return self.node_stack[-levels - 1]
        return None
    
    def get_node_depth(self) -> int:
        """获取当前节点深度"""
        return len(self.node_stack) - 1
    
    def is_in_function(self) -> bool:
        """检查是否在函数内部"""
        for node in reversed(self.node_stack):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return True
        return False
    
    def is_in_class(self) -> bool:
        """检查是否在类内部"""
        for node in reversed(self.node_stack):
            if isinstance(node, ast.ClassDef):
                return True
        return False
```

### 1.2 专用Visitor类
```python
class ImportVisitor(BaseASTVisitor):
    """导入语句Visitor"""
    
    def __init__(self):
        super().__init__()
        self.imports: Dict[str, "ImportInfo"] = {}
        self.imported_names: Set[str] = set()
    
    def visit_Import(self, node: ast.Import):
        """处理import语句"""
        for alias in node.names:
            import_info = ImportInfo(
                module_name=alias.name,
                alias=alias.asname,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_used=False
            )
            self.imports[alias.name] = import_info
            
            # 记录导入的名称
            if alias.asname:
                self.imported_names.add(alias.asname)
            else:
                # 对于from module import name，只记录最后一个部分
                name_parts = alias.name.split('.')
                self.imported_names.add(name_parts[-1])
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """处理from ... import语句"""
        module_name = node.module or ""
        
        for alias in node.names:
            full_name = f"{module_name}.{alias.name}" if module_name else alias.name
            
            import_info = ImportInfo(
                module_name=full_name,
                alias=alias.asname,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_used=False
            )
            self.imports[full_name] = import_info
            
            # 记录导入的名称
            if alias.asname:
                self.imported_names.add(alias.asname)
            else:
                self.imported_names.add(alias.name)
        
        self.generic_visit(node)
    
    def mark_import_as_used(self, name: str):
        """标记导入为已使用"""
        for import_info in self.imports.values():
            if import_info.alias == name or import_info.module_name.endswith(f".{name}"):
                import_info.is_used = True
                break

class VariableVisitor(BaseASTVisitor):
    """变量Visitor"""
    
    def __init__(self):
        super().__init__()
        self.variables: Dict[str, "VariableInfo"] = {}
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        old_function = self.current_function
        self.current_function = node.name
        
        # 记录函数参数
        for arg in node.args.args:
            arg_name = arg.arg
            self._record_variable(arg_name, "parameter", node.lineno)
        
        # 处理函数体
        self.generic_visit(node)
        
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """处理异步函数定义"""
        self.visit_FunctionDef(node)  # 复用相同逻辑
    
    def visit_Name(self, node: ast.Name):
        """处理名称（变量引用）"""
        var_name = node.id
        
        if isinstance(node.ctx, ast.Store):
            # 变量赋值
            self._record_variable(var_name, "variable", node.lineno)
        elif isinstance(node.ctx, ast.Load):
            # 变量使用
            self._mark_variable_as_used(var_name)
        
        self.generic_visit(node)
    
    def _record_variable(self, name: str, var_type: str, lineno: int):
        """记录变量"""
        if name not in self.variables:
            self.variables[name] = VariableInfo(
                name=name,
                var_type=var_type,
                defined_at=lineno,
                is_used=False,
                scope_function=self.current_function,
                scope_class=self.current_class
            )
    
    def _mark_variable_as_used(self, name: str):
        """标记变量为已使用"""
        if name in self.variables:
            self.variables[name].is_used = True

class FunctionVisitor(BaseASTVisitor):
    """函数Visitor"""
    
    def __init__(self):
        super().__init__()
        self.functions: Dict[str, "FunctionInfo"] = {}
        self.current_function_lines: List[int] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        # 计算函数行数
        start_line = node.lineno
        end_line = self._get_node_end_line(node)
        line_count = end_line - start_line + 1
        
        # 记录函数信息
        function_info = FunctionInfo(
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            line_count=line_count,
            args_count=len(node.args.args),
            has_decorators=bool(node.decorator_list)
        )
        self.functions[node.name] = function_info
        
        # 检查函数是否过长
        if line_count > 50:
            self.add_issue(CodeIssue(
                issue_type="long_function",
                message=f"函数 '{node.name}' 过长 ({line_count} 行)",
                lineno=start_line,
                col_offset=node.col_offset,
                severity="warning"
            ))
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """处理异步函数定义"""
        self.visit_FunctionDef(node)
    
    def _get_node_end_line(self, node: ast.AST) -> int:
        """获取节点的结束行号"""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # 如果没有end_lineno属性，遍历子节点找到最大的行号
        max_line = node.lineno
        
        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno:
                max_line = max(max_line, child.lineno)
        
        return max_line
```

### 1.3 复合Visitor
```python
class CompositeVisitor(BaseASTVisitor):
    """复合Visitor，组合多个专用Visitor"""
    
    def __init__(self):
        super().__init__()
        self.visitors: List[BaseASTVisitor] = [
            ImportVisitor(),
            VariableVisitor(),
            FunctionVisitor(),
            NestingVisitor()
        ]
    
    def visit(self, node: ast.AST) -> Any:
        """组合所有Visitor的visit方法"""
        # 调用每个Visitor的visit方法
        results = []
        for visitor in self.visitors:
            result = visitor.visit(node)
            if result is not None:
                results.append(result)
        
        # 收集所有Visitor的问题
        for visitor in self.visitors:
            self.issues.extend(visitor.issues)
        
        return results if results else None
    
    def get_import_visitor(self) -> Optional[ImportVisitor]:
        """获取ImportVisitor"""
        for visitor in self.visitors:
            if isinstance(visitor, ImportVisitor):
                return visitor
        return None
    
    def get_variable_visitor(self) -> Optional[VariableVisitor]:
        """获取VariableVisitor"""
        for visitor in self.visitors:
            if isinstance(visitor, VariableVisitor):
                return visitor
        return None
    
    def get_function_visitor(self) -> Optional[FunctionVisitor]:
        """获取FunctionVisitor"""
        for visitor in self.visitors:
            if isinstance(visitor, FunctionVisitor):
                return visitor
        return None
    
    def get_nesting_visitor(self) -> Optional["NestingVisitor"]:
        """获取NestingVisitor"""
        for visitor in self.visitors:
            if isinstance(visitor, NestingVisitor):
                return visitor
        return None
```

## 2. 作用域跟踪

### 2.1 作用域定义
```python
@dataclass
class Scope:
    """作用域"""
    scope_type: str  # "module", "class", "function", "lambda", "comprehension"
    name: Optional[str] = None
    parent: Optional["Scope"] = None
    symbols: Dict[str, "Symbol"] = field(default_factory=dict)
    children: List["Scope"] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    
    def add_symbol(self, symbol: "Symbol"):
        """添加符号到作用域"""
        self.symbols[symbol.name] = symbol
    
    def get_symbol(self, name: str) -> Optional["Symbol"]:
        """获取符号"""
        return self.symbols.get(name)
    
    def has_symbol(self, name: str) -> bool:
        """检查是否有符号"""
        return name in self.symbols
    
    def resolve_symbol(self, name: str) -> Optional["Symbol"]:
        """解析符号（包括父作用域）"""
        current = self
        while current:
            symbol = current.get_symbol(name)
            if symbol:
                return symbol
            current = current.parent
        return None
    
    def get_ancestors(self) -> List["Scope"]:
        """获取所有祖先作用域"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_depth(self) -> int:
        """获取作用域深度"""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

@dataclass
class Symbol:
    """符号（变量、函数、类等）"""
    name: str
    symbol_type: str  # "variable", "function", "class", "parameter", "import"
    defined_at: int  # 行号
    is_used: bool = False
    is_global: bool = False
    is_nonlocal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2.2 作用域管理器
```python
class ScopeManager:
    """作用域管理器"""
    
    def __init__(self):
        self.current_scope: Optional[Scope] = None
        self.root_scope: Optional[Scope] = None
        self.scope_stack: List[Scope] = []
    
    def enter_scope(self, scope_type: str, name: Optional[str] = None, start_line: int = 0):
        """进入新作用域"""
        new_scope = Scope(
            scope_type=scope_type,
            name=name,
            parent=self.current_scope,
            start_line=start_line
        )
        
        if self.current_scope:
            self.current_scope.children.append(new_scope)
        else:
            self.root_scope = new_scope
        
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope
        
        return new_scope
    
    def exit_scope(self, end_line: int = 0):
        """退出当前作用域"""
        if not self.current_scope:
            return None
        
        # 设置结束行号
        self.current_scope.end_line = end_line
        
        # 弹出作用域栈
        exited_scope = self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1] if self.scope_stack else None
        
        return exited_scope
    
    def add_symbol_to_current(self, symbol: Symbol):
        """添加符号到当前作用域"""
        if self.current_scope:
            self.current_scope.add_symbol(symbol)
    
    def resolve_symbol(self, name: str) -> Optional[Symbol]:
        """解析符号"""
        if self.current_scope:
            return self.current_scope.resolve_symbol(name)
        return None
    
    def mark_symbol_as_used(self, name: str):
        """标记符号为已使用"""
        symbol = self.resolve_symbol(name)
        if symbol:
            symbol.is_used = True
    
    def get_current_scope_depth(self) -> int:
        """获取当前作用域深度"""
        if self.current_scope:
            return self.current_scope.get_depth()
        return 0
    
    def get_all_scopes(self) -> List[Scope]:
        """获取所有作用域（广度优先）"""
        if not self.root_scope:
            return []
        
        all_scopes = []
        queue = [self.root_scope]
        
        while queue:
            current = queue.pop(0)
            all_scopes.append(current)
            queue.extend(current.children)
        
        return all_scopes
    
    def find_unused_symbols(self) -> List[Symbol]:
        """查找未使用的符号"""
        unused = []
        
        for scope in self.get_all_scopes():
            for symbol in scope.symbols.values():
                if not symbol.is_used and symbol.symbol_type in ["variable", "parameter"]:
                    unused.append(symbol)
        
        return unused
```

### 2.3 未使用检测策略
```python
class UnusedDetectionVisitor(BaseASTVisitor):
    """未使用检测Visitor"""
    
    def __init__(self, scope_manager: ScopeManager):
        super().__init__()
        self.scope_manager = scope_manager
        self.import_aliases: Dict[str, str] = {}  # 别名到原始名称的映射
    
    def visit_Import(self, node: ast.Import):
        """处理import语句"""
        for alias in node.names:
            symbol = Symbol(
                name=alias.asname or alias.name,
                symbol_type="import",
                defined_at=node.lineno,
                is_used=False
            )
            
            # 记录别名映射
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
            
            self.scope_manager.add_symbol_to_current(symbol)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """处理from ... import语句"""
        module_name = node.module or ""
        
        for alias in node.names:
            full_name = f"{module_name}.{alias.name}" if module_name else alias.name
            symbol_name = alias.asname or alias.name
            
            symbol = Symbol(
                name=symbol_name,
                symbol_type="import",
                defined_at=node.lineno,
                is_used=False,
                metadata={"full_name": full_name}
            )
            
            # 记录别名映射
            if alias.asname:
                self.import_aliases[alias.asname] = full_name
            
            self.scope_manager.add_symbol_to_current(symbol)
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        # 进入函数作用域
        self.scope_manager.enter_scope("function", node.name, node.lineno)
        
        # 添加参数符号
        for arg in node.args.args:
            symbol = Symbol(
                name=arg.arg,
                symbol_type="parameter",
                defined_at=node.lineno,
                is_used=False
            )
            self.scope_manager.add_symbol_to_current(symbol)
        
        # 处理函数体
        self.generic_visit(node)
        
        # 退出函数作用域
        self.scope_manager.exit_scope(node.end_lineno or node.lineno)
    
    def visit_Name(self, node: ast.Name):
        """处理名称引用"""
        if isinstance(node.ctx, ast.Load):
            # 变量使用
            self.scope_manager.mark_symbol_as_used(node.id)
            
            # 检查是否是导入的别名
            if node.id in self.import_aliases:
                # 也标记原始导入为已使用
                original_name = self.import_aliases[node.id]
                self.scope_manager.mark_symbol_as_used(original_name)
        
        elif isinstance(node.ctx, ast.Store):
            # 变量定义
            symbol = Symbol(
                name=node.id,
                symbol_type="variable",
                defined_at=node.lineno,
                is_used=False
            )
            self.scope_manager.add_symbol_to_current(symbol)
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        """处理属性访问"""
        # 检查是否是模块属性访问（如os.path）
        if isinstance(node.value, ast.Name):
            module_name = node.value.id
            self.scope_manager.mark_symbol_as_used(module_name)
        
        self.generic_visit(node)
    
    def get_unused_imports(self) -> List[Symbol]:
        """获取未使用的导入"""
        unused = []
        
        for scope in self.scope_manager.get_all_scopes():
            for symbol in scope.symbols.values():
                if symbol.symbol_type == "import" and not symbol.is_used:
                    unused.append(symbol)
        
        return unused
    
    def get_unused_variables(self) -> List[Symbol]:
        """获取未使用的变量"""
        return self.scope_manager.find_unused_symbols()
```

## 3. 嵌套深度计算方法

### 3.1 嵌套深度Visitor
```python
class NestingVisitor(BaseASTVisitor):
    """嵌套深度Visitor"""
    
    def __init__(self):
        super().__init__()
        self.max_nesting_depth: int = 0
        self.nesting_info: Dict[str, Dict[str, Any]] = {}
        self.current_block_stack: List[Dict[str, Any]] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        # 进入函数块
        self._enter_block("function", node.name, node.lineno)
        
        # 处理函数体
        self.generic_visit(node)
        
        # 退出函数块
        block_info = self._exit_block()
        
        # 记录函数嵌套信息
        self.nesting_info[f"function:{node.name}"] = block_info
        
        # 检查嵌套深度
        if block_info["max_depth"] > 4:
            self.add_issue(CodeIssue(
                issue_type="deep_nesting",
                message=f"函数 '{node.name}' 嵌套深度过大 ({block_info['max_depth']} 层)",
                lineno=node.lineno,
                col_offset=node.col_offset,
                severity="warning"
            ))
    
    def visit_If(self, node: ast.If):
        """处理if语句"""
        self._enter_block("if", "", node.lineno)
        
        # 处理条件
        self.visit(node.test)
        
        # 处理if体
        for stmt in node.body:
            self.visit(stmt)
        
        # 处理elif分支
        for elif_stmt in node.orelse:
            if isinstance(elif_stmt, ast.If):
                self.visit(elif_stmt)
            else:
                # else分支
                self._enter_block("else", "", elif_stmt.lineno if hasattr(elif_stmt, 'lineno') else node.lineno)
                self.visit(elif_stmt)
                self._exit_block()
        
        self._exit_block()
    
    def visit_For(self, node: ast.For):
        """处理for循环"""
        self._enter_block("for", "", node.lineno)
        
        # 处理迭代目标和可迭代对象
        self.visit(node.target)
        self.visit(node.iter)
        
        # 处理循环体
        for stmt in node.body:
            self.visit(stmt)
        
        # 处理else分支
        if node.orelse:
            self._enter_block("else", "", node.orelse[0].lineno)
            for stmt in node.orelse:
                self.visit(stmt)
            self._exit_block()
        
        self._exit_block()
    
    def visit_While(self, node: ast.While):
        """处理while循环"""
        self._enter_block("while", "", node.lineno)
        
        # 处理条件
        self.visit(node.test)
        
        # 处理循环体
        for stmt in node.body:
            self.visit(stmt)
        
        # 处理else分支
        if node.orelse:
            self._enter_block("else", "", node.orelse[0].lineno)
            for stmt in node.orelse:
                self.visit(stmt)
            self._exit_block()
        
        self._exit_block()
    
    def visit_Try(self, node: ast.Try):
        """处理try语句"""
        self._enter_block("try", "", node.lineno)
        
        # 处理try体
        for stmt in node.body:
            self.visit(stmt)
        
        # 处理except分支
        for handler in node.handlers:
            self._enter_block("except", "", handler.lineno)
            self.visit(handler)
            self._exit_block()
        
        # 处理else分支
        if node.orelse:
            self._enter_block("else", "", node.orelse[0].lineno)
            for stmt in node.orelse:
                self.visit(stmt)
            self._exit_block()
        
        # 处理finally分支
        if node.finalbody:
            self._enter_block("finally", "", node.finalbody[0].lineno)
            for stmt in node.finalbody:
                self.visit(stmt)
            self._exit_block()
        
        self._exit_block()
    
    def _enter_block(self, block_type: str, block_name: str, lineno: int):
        """进入代码块"""
        block_info = {
            "type": block_type,
            "name": block_name,
            "start_line": lineno,
            "depth": len(self.current_block_stack),
            "max_depth": len(self.current_block_stack) + 1
        }
        
        self.current_block_stack.append(block_info)
        
        # 更新最大嵌套深度
        current_depth = len(self.current_block_stack)
        if current_depth > self.max_nesting_depth:
            self.max_nesting_depth = current_depth
    
    def _exit_block(self) -> Dict[str, Any]:
        """退出代码块"""
        if self.current_block_stack:
            block_info = self.current_block_stack.pop()
            
            # 更新父块的最大深度
            if self.current_block_stack:
                parent_block = self.current_block_stack[-1]
                if block_info["max_depth"] > parent_block["max_depth"]:
                    parent_block["max_depth"] = block_info["max_depth"]
            
            return block_info
        
        return {}
    
    def get_max_nesting_depth(self) -> int:
        """获取最大嵌套深度"""
        return self.max_nesting_depth
    
    def get_nesting_summary(self) -> Dict[str, Any]:
        """获取嵌套摘要"""
        return {
            "max_depth": self.max_nesting_depth,
            "blocks": list(self.nesting_info.values()),
            "has_deep_nesting": self.max_nesting_depth > 4
        }
```

### 3.2 嵌套深度分析器
```python
class NestingAnalyzer:
    """嵌套深度分析器"""
    
    def __init__(self):
        self.visitor = NestingVisitor()
    
    def analyze(self, source_code: str) -> Dict[str, Any]:
        """分析源代码的嵌套深度"""
        try:
            tree = ast.parse(source_code)
            self.visitor.visit(tree)
            
            return {
                "max_nesting_depth": self.visitor.get_max_nesting_depth(),
                "nesting_summary": self.visitor.get_nesting_summary(),
                "issues": [issue.to_dict() for issue in self.visitor.issues],
                "success": True
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"语法错误: {e}",
                "max_nesting_depth": 0,
                "issues": []
            }
    
    def check_function_nesting(self, function_node: ast.FunctionDef) -> Dict[str, Any]:
        """检查函数的嵌套深度"""
        # 创建新的Visitor用于此函数
        func_visitor = NestingVisitor()
        func_visitor.visit(function_node)
        
        max_depth = func_visitor.get_max_nesting_depth()
        
        return {
            "function_name": function_node.name,
            "max_nesting_depth": max_depth,
            "has_deep_nesting": max_depth > 4,
            "start_line": function_node.lineno,
            "end_line": function_node.end_lineno or function_node.lineno
        }
    
    def find_deeply_nested_blocks(self, source_code: str) -> List[Dict[str, Any]]:
        """查找深度嵌套的代码块"""
        try:
            tree = ast.parse(source_code)
            deeply_nested = []
            
            # 遍历AST查找深度嵌套的块
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.FunctionDef)):
                    # 分析此节点的嵌套深度
                    block_visitor = NestingVisitor()
                    block_visitor.visit(node)
                    
                    if block_visitor.get_max_nesting_depth() > 4:
                        block_info = {
                            "type": type(node).__name__,
                            "lineno": node.lineno,
                            "max_depth": block_visitor.get_max_nesting_depth(),
                            "name": getattr(node, 'name', '')
                        }
                        deeply_nested.append(block_info)
            
            return deeply_nested
        except SyntaxError:
            return []
```

### 3.3 嵌套重构建议
```python
class NestingRefactoringAdvisor:
    """嵌套重构建议器"""
    
    def __init__(self):
        self.suggestions: List[Dict[str, Any]] = []
    
    def analyze_for_refactoring(self, nesting_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析嵌套信息并给出重构建议"""
        suggestions = []
        
        for block_key, block_data in nesting_info.get("blocks", {}).items():
            if block_data.get("max_depth", 0) > 4:
                suggestion = self._create_refactoring_suggestion(block_key, block_data)
                suggestions.append(suggestion)
        
        return suggestions
    
    def _create_refactoring_suggestion(self, block_key: str, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建重构建议"""
        block_type = block_data.get("type", "")
        max_depth = block_data.get("max_depth", 0)
        start_line = block_data.get("start_line", 0)
        
        suggestion = {
            "block_key": block_key,
            "block_type": block_type,
            "max_depth": max_depth,
            "start_line": start_line,
            "suggestions": [],
            "priority": "high" if max_depth > 6 else "medium"
        }
        
        # 根据嵌套类型给出具体建议
        if max_depth > 6:
            suggestion["suggestions"].append("深度嵌套严重，建议立即重构")
        
        if block_type == "function":
            suggestion["suggestions"].extend([
                "提取深层嵌套的逻辑为独立函数",
                "使用卫语句（Guard Clauses）减少嵌套",
                "考虑使用策略模式或状态模式"
            ])
        elif block_type in ["if", "for", "while"]:
            suggestion["suggestions"].extend([
                "使用提前返回（early return）减少嵌套",
                "将复杂条件提取为函数或变量",
                "考虑使用列表推导式或生成器表达式"
            ])
        elif block_type == "try":
            suggestion["suggestions"].extend([
                "缩小try块的范围",
                "将异常处理逻辑提取为独立函数",
                "使用上下文管理器（context manager）"
            ])
        
        return suggestion
    
    def generate_refactoring_examples(self, block_type: str) -> List[str]:
        """生成重构示例"""
        examples = []
        
        if block_type == "function":
            examples.extend([
                "# 重构前：",
                "def process_data(data):",
                "    if data:",
                "        for item in data:",
                "            if item.valid:",
                "                # 深层嵌套逻辑...",
                "",
                "# 重构后：",
                "def process_item(item):",
                "    if not item.valid:",
                "        return None",
                "    # 处理逻辑...",
                "",
                "def process_data(data):",
                "    if not data:",
                "        return []",
                "    return [process_item(item) for item in data if process_item(item)]"
            ])
        
        return examples
```

## 4. 数据类结果模式

### 4.1 数据类定义
```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class IssueSeverity(str, Enum):
    """问题严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class IssueType(str, Enum):
    """问题类型"""
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    LONG_FUNCTION = "long_function"
    DEEP_NESTING = "deep_nesting"
    COMPLEX_EXPRESSION = "complex_expression"
    DUPLICATE_CODE = "duplicate_code"

@dataclass
class CodeIssue:
    """代码问题"""
    issue_type: IssueType
    message: str
    lineno: int
    col_offset: int
    severity: IssueSeverity
    source_file: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.issue_type.value,
            "message": self.message,
            "lineno": self.lineno,
            "col_offset": self.col_offset,
            "severity": self.severity.value,
            "source_file": self.source_file,
            "suggestion": self.suggestion,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        location = f"{self.source_file}:{self.lineno}" if self.source_file else f"line {self.lineno}"
        return f"[{self.severity.value.upper()}] {location}: {self.message}"

@dataclass
class ImportInfo:
    """导入信息"""
    module_name: str
    alias: Optional[str] = None
    lineno: int = 0
    col_offset: int = 0
    is_used: bool = False
    import_type: str = "import"  # "import" 或 "from_import"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "module": self.module_name,
            "alias": self.alias,
            "lineno": self.lineno,
            "is_used": self.is_used,
            "import_type": self.import_type
        }

@dataclass
class VariableInfo:
    """变量信息"""
    name: str
    var_type: str  # "variable", "parameter", "class_variable"
    defined_at: int
    is_used: bool = False
    scope_function: Optional[str] = None
    scope_class: Optional[str] = None
    is_global: bool = False
    is_nonlocal: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.var_type,
            "defined_at": self.defined_at,
            "is_used": self.is_used,
            "scope": {
                "function": self.scope_function,
                "class": self.scope_class
            },
            "modifiers": {
                "global": self.is_global,
                "nonlocal": self.is_nonlocal
            }
        }

@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    start_line: int
    end_line: int
    line_count: int
    args_count: int = 0
    has_decorators: bool = False
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    nesting_depth: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "lines": {
                "start": self.start_line,
                "end": self.end_line,
                "count": self.line_count
            },
            "args_count": self.args_count,
            "has_decorators": self.has_decorators,
            "return_type": self.return_type,
            "has_docstring": bool(self.docstring),
            "nesting_depth": self.nesting_depth
        }

@dataclass
class CodeAnalysisResult:
    """代码分析结果"""
    source_file: str
    issues: List[CodeIssue]
    imports: List[ImportInfo]
    variables: List[VariableInfo]
    functions: List[FunctionInfo]
    nesting_summary: Dict[str, Any]
    analysis_time: float
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_file": self.source_file,
            "success": self.success,
            "error_message": self.error_message,
            "analysis_time": self.analysis_time,
            "summary": self._create_summary(),
            "issues": [issue.to_dict() for issue in self.issues],
            "imports": [imp.to_dict() for imp in self.imports],
            "variables": [var.to_dict() for var in self.variables],
            "functions": [func.to_dict() for func in self.functions],
            "nesting": self.nesting_summary
        }
    
    def _create_summary(self) -> Dict[str, Any]:
        """创建摘要"""
        issue_counts = {}
        for issue in self.issues:
            issue_type = issue.issue_type.value
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        return {
            "total_issues": len(self.issues),
            "issue_counts": issue_counts,
            "unused_imports": sum(1 for imp in self.imports if not imp.is_used),
            "unused_variables": sum(1 for var in self.variables if not var.is_used),
            "long_functions": sum(1 for func in self.functions if func.line_count > 50),
            "total_functions": len(self.functions),
            "max_nesting_depth": self.nesting_summary.get("max_depth", 0)
        }
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[CodeIssue]:
        """按严重程度获取问题"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return any(issue.severity == IssueSeverity.ERROR for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """检查是否有警告"""
        return any(issue.severity == IssueSeverity.WARNING for issue in self.issues)
```

### 4.2 结果生成器
```python
class ResultGenerator:
    """结果生成器"""
    
    def __init__(self):
        self.formatters: Dict[str, callable] = {
            "json": self._format_json,
            "text": self._format_text,
            "markdown": self._format_markdown,
            "html": self._format_html
        }
    
    def generate_report(
        self,
        result: CodeAnalysisResult,
        format_type: str = "json"
    ) -> str:
        """生成报告"""
        formatter = self.formatters.get(format_type)
        if not formatter:
            raise ValueError(f"不支持的报告格式: {format_type}")
        
        return formatter(result)
    
    def _format_json(self, result: CodeAnalysisResult) -> str:
        """格式化为JSON"""
        import json
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    
    def _format_text(self, result: CodeAnalysisResult) -> str:
        """格式化为文本"""
        lines = []
        
        # 标题
        lines.append(f"代码分析报告: {result.source_file}")
        lines.append("=" * 60)
        
        # 摘要
        summary = result._create_summary()
        lines.append("\n摘要:")
        lines.append(f"  总问题数: {summary['total_issues']}")
        lines.append(f"  未使用导入: {summary['unused_imports']}")
        lines.append(f"  未使用变量: {summary['unused_variables']}")
        lines.append(f"  过长函数: {summary['long_functions']}")
        lines.append(f"  最大嵌套深度: {summary['max_nesting_depth']}")
        
        # 详细问题
        if result.issues:
            lines.append("\n详细问题:")
            for issue in result.issues:
                lines.append(f"  {issue}")
        
        # 未使用导入
        unused_imports = [imp for imp in result.imports if not imp.is_used]
        if unused_imports:
            lines.append("\n未使用导入:")
            for imp in unused_imports:
                lines.append(f"  第{imp.lineno}行: {imp.module_name}")
        
        # 未使用变量
        unused_vars = [var for var in result.variables if not var.is_used]
        if unused_vars:
            lines.append("\n未使用变量:")
            for var in unused_vars:
                lines.append(f"  {var.name} (第{var.defined_at}行)")
        
        return "\n".join(lines)
    
    def _format_markdown(self, result: CodeAnalysisResult) -> str:
        """格式化为Markdown"""
        lines = ["# 代码分析报告\n"]
        
        # 摘要表格
        summary = result._create_summary()
        lines.append("## 摘要\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总问题数 | {summary['total_issues']} |")
        lines.append(f"| 未使用导入 | {summary['unused_imports']} |")
        lines.append(f"| 未使用变量 | {summary['unused_variables']} |")
        lines.append(f"| 过长函数 | {summary['long_functions']} |")
        lines.append(f"| 最大嵌套深度 | {summary['max_nesting_depth']} |")
        
        # 问题列表
        if result.issues:
            lines.append("\n## 问题列表\n")
            lines.append("| 行号 | 类型 | 严重程度 | 描述 |")
            lines.append("|------|------|----------|------|")
            
            for issue in sorted(result.issues, key=lambda x: x.lineno):
                lines.append(f"| {issue.lineno} | {issue.issue_type.value} | {issue.severity.value} | {issue.message} |")
        
        return "\n".join(lines)
    
    def _format_html(self, result: CodeAnalysisResult) -> str:
        """格式化为HTML"""
        # 简化实现，实际应用中可以使用模板引擎
        summary = result._create_summary()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>代码分析报告 - {result.source_file}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .issue {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }}
                .error {{ border-left-color: #d9534f; }}
                .warning {{ border-left-color: #f0ad4e; }}
                .info {{ border-left-color: #5bc0de; }}
            </style>
        </head>
        <body>
            <h1>代码分析报告: {result.source_file}</h1>
            
            <div class="summary">
                <h2>摘要</h2>
                <p>总问题数: {summary['total_issues']}</p>
                <p>未使用导入: {summary['unused_imports']}</p>
                <p>未使用变量: {summary['unused_variables']}</p>
                <p>过长函数: {summary['long_functions']}</p>
                <p>最大嵌套深度: {summary['max_nesting_depth']}</p>
            </div>
            
            <h2>详细问题</h2>
        """
        
        for issue in result.issues:
            severity_class = issue.severity.value
            html += f"""
            <div class="issue {severity_class}">
                <strong>第{issue.lineno}行</strong>: {issue.message}<br>
                <small>类型: {issue.issue_type.value}, 严重程度: {issue.severity.value}</small>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
```

## 5. 约束确认

### 5.1 Python 3.10+, stdlib only
- 要求Python 3.10或更高版本
- 仅使用标准库
- 无外部依赖

### 5.2 ast.NodeVisitor required, no regex
- 必须使用ast.NodeVisitor
- 使用Python的AST模块进行代码分析
- 不使用正则表达式进行代码解析

### 5.3 Results as dataclass
- 所有结果使用数据类表示
- 类型安全的数据结构
- 易于序列化和反序列化

### 5.4 Full type annotations
- 完整的类型注解
- 使用mypy兼容的类型提示
- 类型安全的API设计

### 5.5 Check: unused import/var, long func, deep nest
- 检查未使用的导入
- 检查未使用的变量
- 检查过长的函数（>50行）
- 检查深度嵌套（>4层）

### 5.6 Single file, class output
- 所有代码在单个Python文件中
- 输出为类定义
- 自包含代码检查器实现