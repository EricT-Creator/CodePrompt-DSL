import ast
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from collections import defaultdict

@dataclass
class CodeIssue:
    """代码问题"""
    type: str  # 'unused_import', 'unused_variable', 'long_function', 'deep_nesting'
    message: str
    line: int
    column: int
    severity: str  # 'warning' or 'error'
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CheckResults:
    """检查结果"""
    issues: List[CodeIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def add_issue(self, issue: CodeIssue):
        """添加问题"""
        self.issues.append(issue)
        issue_type = issue.type
        if issue_type not in self.summary:
            self.summary[issue_type] = 0
        self.summary[issue_type] += 1
    
    def __str__(self) -> str:
        """字符串表示"""
        lines = []
        lines.append("Code Check Results:")
        lines.append("=" * 50)
        
        # 按行号排序问题
        sorted_issues = sorted(self.issues, key=lambda x: (x.line, x.column))
        
        for issue in sorted_issues:
            lines.append(f"Line {issue.line}:{issue.column} [{issue.severity.upper()}] {issue.type}")
            lines.append(f"  {issue.message}")
            if issue.details:
                for key, value in issue.details.items():
                    lines.append(f"    {key}: {value}")
            lines.append("")
        
        lines.append("Summary:")
        lines.append("-" * 20)
        for issue_type, count in sorted(self.summary.items()):
            lines.append(f"  {issue_type}: {count}")
        
        total_issues = sum(self.summary.values())
        lines.append(f"\nTotal issues found: {total_issues}")
        
        return "\n".join(lines)

class CodeCheckerVisitor(ast.NodeVisitor):
    """AST访问器，用于检测代码问题"""
    
    def __init__(self):
        super().__init__()
        self.results = CheckResults()
        
        # 跟踪变量使用
        self.variable_defs: Dict[str, List[Dict]] = {}  # 变量定义位置
        self.variable_uses: Set[str] = set()  # 已使用的变量
        
        # 跟踪导入
        self.imports: Dict[str, List[Dict]] = {}  # 导入项及其位置
        
        # 函数嵌套深度
        self.current_function: Optional[str] = None
        self.function_lines: Dict[str, int] = {}  # 函数行数
        self.function_start_line: Dict[str, int] = {}  # 函数开始行
        
        # 嵌套深度
        self.nesting_level: int = 0
        self.max_nesting_in_function: Dict[str, int] = {}
        
        # 当前作用域
        self.current_scope: List[str] = []  # 作用域栈
        
    def _add_issue(self, issue_type: str, message: str, node: ast.AST, severity: str = "warning", **details):
        """添加问题"""
        issue = CodeIssue(
            type=issue_type,
            message=message,
            line=node.lineno,
            column=node.col_offset if hasattr(node, 'col_offset') else 0,
            severity=severity,
            details=details
        )
        self.results.add_issue(issue)
    
    def _enter_scope(self, name: str):
        """进入新作用域"""
        self.current_scope.append(name)
    
    def _exit_scope(self):
        """退出作用域"""
        if self.current_scope:
            self.current_scope.pop()
    
    def _get_full_name(self, name: str) -> str:
        """获取带作用域前缀的完整名称"""
        if self.current_scope:
            return f"{'.'.join(self.current_scope)}.{name}"
        return name
    
    def visit_Import(self, node: ast.Import):
        """处理 import 语句"""
        for alias in node.names:
            import_name = alias.name
            asname = alias.asname if alias.asname else import_name
            
            # 记录导入
            if asname not in self.imports:
                self.imports[asname] = []
            
            self.imports[asname].append({
                'line': node.lineno,
                'name': import_name,
                'asname': asname,
                'node': node
            })
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """处理 from ... import 语句"""
        module = node.module if node.module else ""
        
        for alias in node.names:
            import_name = alias.name
            asname = alias.asname if alias.asname else import_name
            full_name = f"{module}.{import_name}" if module else import_name
            
            # 记录导入
            if asname not in self.imports:
                self.imports[asname] = []
            
            self.imports[asname].append({
                'line': node.lineno,
                'name': full_name,
                'asname': asname,
                'node': node
            })
        
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """处理变量名使用"""
        if isinstance(node.ctx, ast.Load):  # 读取变量
            var_name = node.id
            self.variable_uses.add(self._get_full_name(var_name))
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        # 进入函数作用域
        self._enter_scope(node.name)
        self.current_function = node.name
        
        # 记录函数开始行
        self.function_start_line[node.name] = node.lineno
        self.max_nesting_in_function[node.name] = self.nesting_level
        
        # 处理参数
        for arg in node.args.args:
            arg_name = arg.arg
            full_name = self._get_full_name(arg_name)
            if full_name not in self.variable_defs:
                self.variable_defs[full_name] = []
            self.variable_defs[full_name].append({
                'line': node.lineno,
                'type': 'parameter',
                'node': arg
            })
        
        # 处理函数体
        self.generic_visit(node.body)
        
        # 计算函数行数
        if node.body:
            last_node = node.body[-1]
            end_line = last_node.lineno if hasattr(last_node, 'lineno') else node.lineno
            self.function_lines[node.name] = end_line - node.lineno + 1
            
            # 检查函数长度
            if self.function_lines[node.name] > 50:
                self._add_issue(
                    'long_function',
                    f"Function '{node.name}' is too long ({self.function_lines[node.name]} lines)",
                    node,
                    severity='warning',
                    lines=self.function_lines[node.name],
                    limit=50
                )
        
        # 退出函数作用域
        self._exit_scope()
        self.current_function = None
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """处理异步函数定义"""
        # 与普通函数相同处理
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """处理类定义"""
        # 进入类作用域
        self._enter_scope(node.name)
        
        # 处理类体
        self.generic_visit(node.body)
        
        # 退出类作用域
        self._exit_scope()
    
    def visit_Assign(self, node: ast.Assign):
        """处理赋值语句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                full_name = self._get_full_name(var_name)
                
                if full_name not in self.variable_defs:
                    self.variable_defs[full_name] = []
                
                self.variable_defs[full_name].append({
                    'line': node.lineno,
                    'type': 'assignment',
                    'node': target
                })
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        """处理for循环"""
        self.nesting_level += 1
        
        # 检查嵌套深度
        if self.current_function and self.nesting_level > 4:
            self._add_issue(
                'deep_nesting',
                f"Nesting depth {self.nesting_level} exceeds limit",
                node,
                severity='warning',
                depth=self.nesting_level,
                limit=4
            )
        
        # 记录循环变量
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            full_name = self._get_full_name(var_name)
            if full_name not in self.variable_defs:
                self.variable_defs[full_name] = []
            self.variable_defs[full_name].append({
                'line': node.lineno,
                'type': 'loop_variable',
                'node': node.target
            })
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node: ast.While):
        """处理while循环"""
        self.nesting_level += 1
        
        if self.current_function and self.nesting_level > 4:
            self._add_issue(
                'deep_nesting',
                f"Nesting depth {self.nesting_level} exceeds limit",
                node,
                severity='warning',
                depth=self.nesting_level,
                limit=4
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_If(self, node: ast.If):
        """处理if语句"""
        self.nesting_level += 1
        
        if self.current_function and self.nesting_level > 4:
            self._add_issue(
                'deep_nesting',
                f"Nesting depth {self.nesting_level} exceeds limit",
                node,
                severity='warning',
                depth=self.nesting_level,
                limit=4
            )
        
        self.generic_visit(node.body)
        
        # 处理elif分支
        for elif_node in node.orelse:
            if isinstance(elif_node, ast.If):
                self.visit_If(elif_node)
        
        # 处理else分支
        for else_node in node.orelse:
            if not isinstance(else_node, ast.If):
                self.generic_visit([else_node])
        
        self.nesting_level -= 1
    
    def visit_Try(self, node: ast.Try):
        """处理try语句"""
        self.nesting_level += 1
        
        if self.current_function and self.nesting_level > 4:
            self._add_issue(
                'deep_nesting',
                f"Nesting depth {self.nesting_level} exceeds limit",
                node,
                severity='warning',
                depth=self.nesting_level,
                limit=4
            )
        
        # 处理try块
        self.generic_visit(node.body)
        
        # 处理except块
        for handler in node.handlers:
            if handler.name:
                var_name = handler.name
                full_name = self._get_full_name(var_name)
                if full_name not in self.variable_defs:
                    self.variable_defs[full_name] = []
                self.variable_defs[full_name].append({
                    'line': node.lineno,
                    'type': 'exception_variable',
                    'node': handler
                })
            self.generic_visit(handler.body)
        
        # 处理else块
        if node.orelse:
            self.generic_visit(node.orelse)
        
        # 处理finally块
        if node.finalbody:
            self.generic_visit(node.finalbody)
        
        self.nesting_level -= 1
    
    def visit_With(self, node: ast.With):
        """处理with语句"""
        self.nesting_level += 1
        
        if self.current_function and self.nesting_level > 4:
            self._add_issue(
                'deep_nesting',
                f"Nesting depth {self.nesting_level} exceeds limit",
                node,
                severity='warning',
                depth=self.nesting_level,
                limit=4
            )
        
        # 处理上下文管理器变量
        for item in node.items:
            if item.optional_vars:
                if isinstance(item.optional_vars, ast.Name):
                    var_name = item.optional_vars.id
                    full_name = self._get_full_name(var_name)
                    if full_name not in self.variable_defs:
                        self.variable_defs[full_name] = []
                    self.variable_defs[full_name].append({
                        'line': node.lineno,
                        'type': 'context_variable',
                        'node': item.optional_vars
                    })
        
        self.generic_visit(node.body)
        self.nesting_level -= 1
    
    def _check_unused_items(self):
        """检查未使用的项"""
        # 检查未使用的导入
        for import_name, import_info_list in self.imports.items():
            full_import_name = self._get_full_name(import_name)
            if full_import_name not in self.variable_uses:
                for import_info in import_info_list:
                    self._add_issue(
                        'unused_import',
                        f"Unused import '{import_info['name']}'",
                        import_info['node'],
                        severity='warning',
                        import_name=import_info['name'],
                        asname=import_info['asname']
                    )
        
        # 检查未使用的变量
        for var_name, defs_list in self.variable_defs.items():
            if var_name not in self.variable_uses:
                for def_info in defs_list:
                    # 跳过某些特殊情况（如_开头的变量）
                    if '_' in var_name and var_name.split('.')[-1].startswith('_'):
                        continue
                    
                    self._add_issue(
                        'unused_variable',
                        f"Unused variable '{var_name.split('.')[-1]}'",
                        def_info['node'],
                        severity='warning',
                        variable_name=var_name.split('.')[-1],
                        definition_type=def_info['type']
                    )

def check_code(source: str) -> CheckResults:
    """检查代码并返回结果"""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        # 如果源代码有语法错误，创建包含语法错误的结果
        results = CheckResults()
        results.add_issue(CodeIssue(
            type='syntax_error',
            message=f"Syntax error: {e.msg}",
            line=e.lineno or 1,
            column=e.offset or 0,
            severity='error',
            details={'error': str(e)}
        ))
        return results
    
    visitor = CodeCheckerVisitor()
    visitor.visit(tree)
    visitor._check_unused_items()
    
    return visitor.results


# 使用示例
if __name__ == "__main__":
    # 示例代码
    sample_code = '''
import os
import sys
from datetime import datetime
from typing import List, Dict

import numpy as np  # 未使用的导入
import pandas as pd  # 未使用的导入

unused_global = 42  # 未使用的全局变量

def very_long_function():
    """这是一个很长的函数"""
    # 第一行
    x = 1
    y = 2
    z = 3
    a = 4
    b = 5
    c = 6
    d = 7
    e = 8
    f = 9
    g = 10
    h = 11
    i = 12
    j = 13
    k = 14
    l = 15
    m = 16
    n = 17
    o = 18
    p = 19
    q = 20
    r = 21
    s = 22
    t = 23
    u = 24
    v = 25
    w = 26
    x1 = 27
    y1 = 28
    z1 = 29
    a1 = 30
    b1 = 31
    c1 = 32
    d1 = 33
    e1 = 34
    f1 = 35
    g1 = 36
    h1 = 37
    i1 = 38
    j1 = 39
    k1 = 40
    l1 = 41
    m1 = 42
    n1 = 43
    o1 = 44
    p1 = 45
    q1 = 46
    r1 = 47
    s1 = 48
    t1 = 49
    u1 = 50
    v1 = 51  # 超过50行
    
    unused_local = 100  # 未使用的局部变量
    
    # 深度嵌套示例
    for i in range(10):
        if i > 5:
            while True:
                try:
                    with open("test.txt", "r") as f:
                        if f.read():
                            print("Too deep!")  # 嵌套深度5
                except:
                    pass

def normal_function(items: List[str]) -> Dict[str, int]:
    """正常函数示例"""
    result = {}
    for item in items:
        result[item] = len(item)
    return result

def another_function():
    """另一个函数，使用了导入"""
    current_time = datetime.now()
    print(f"Current directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    return current_time

class MyClass:
    """示例类"""
    def __init__(self):
        self.value = 0
        unused_member = 99  # 未使用的成员变量
    
    def method_with_unused_param(self, unused_param):
        """有未使用参数的方法"""
        return self.value
'''

    print("检查示例代码:")
    print("=" * 60)
    results = check_code(sample_code)
    print(results)
    
    # 测试自定义代码
    print("\n" + "=" * 60)
    print("测试自定义代码检查:")
    
    test_code = input("请输入要检查的Python代码（或按Enter使用默认代码）:\n")
    if not test_code.strip():
        test_code = '''
def test():
    x = 1
    y = 2  # 未使用
    print(x)
    
    import json  # 未使用
    import math
    
    return math.sqrt(x)
'''
    
    print("\n检查结果:")
    print("-" * 40)
    results = check_code(test_code)
    print(results)
    
    # 保存结果到文件
    with open('code_check_results.txt', 'w') as f:
        f.write(str(results))
    print("\n结果已保存到 'code_check_results.txt'")