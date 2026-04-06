import ast
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from enum import Enum

class IssueType(Enum):
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    LONG_FUNCTION = "long_function"
    DEEP_NESTING = "deep_nesting"

@dataclass
class CodeIssue:
    """代码问题"""
    issue_type: IssueType
    message: str
    line: int
    column: int
    node_name: str = ""
    details: Dict = field(default_factory=dict)

@dataclass
class CheckResults:
    """检查结果"""
    issues: List[CodeIssue] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    
    def add_issue(self, issue: CodeIssue):
        """添加问题"""
        self.issues.append(issue)
    
    def get_issue_count(self) -> int:
        """获取问题总数"""
        return len(self.issues)
    
    def get_issue_summary(self) -> Dict[IssueType, int]:
        """获取问题类型统计"""
        summary = defaultdict(int)
        for issue in self.issues:
            summary[issue.issue_type] += 1
        return dict(summary)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_issues": self.get_issue_count(),
            "issue_summary": self.get_issue_summary(),
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "message": issue.message,
                    "line": issue.line,
                    "column": issue.column,
                    "node_name": issue.node_name,
                    "details": issue.details
                }
                for issue in self.issues
            ]
        }

class CodeCheckerVisitor(ast.NodeVisitor):
    """AST访问器，用于检查代码问题"""
    
    def __init__(self, max_function_length: int = 50, max_nesting_depth: int = 4):
        """
        初始化检查器
        
        Args:
            max_function_length: 函数最大长度（行数）
            max_nesting_depth: 最大嵌套深度
        """
        self.results = CheckResults()
        self.max_function_length = max_function_length
        self.max_nesting_depth = max_nesting_depth
        
        # 跟踪变量使用
        self.imports: Dict[str, Tuple[int, int]] = {}  # name -> (line, column)
        self.used_names: Set[str] = set()
        self.defined_names: Dict[str, Tuple[int, int, str]] = {}  # name -> (line, column, scope)
        
        # 当前作用域栈
        self.scope_stack: List[Set[str]] = []
        self.current_scope_name: str = "module"
        
        # 嵌套深度跟踪
        self.nesting_depth: int = 0
        self.max_current_nesting: int = 0
        
        # 函数长度跟踪
        self.current_function: Optional[ast.FunctionDef] = None
        self.function_start_line: int = 0
    
    def _enter_scope(self, scope_name: str):
        """进入新作用域"""
        self.scope_stack.append(set())
        self.current_scope_name = scope_name
    
    def _exit_scope(self):
        """退出当前作用域"""
        if self.scope_stack:
            # 检查未使用的变量
            scope_vars = self.scope_stack.pop()
            for var_name in scope_vars:
                if var_name not in self.used_names:
                    self._report_unused_variable(var_name)
            
            # 恢复上一级作用域名
            if self.scope_stack:
                self.current_scope_name = "anonymous"
            else:
                self.current_scope_name = "module"
    
    def _report_unused_variable(self, var_name: str):
        """报告未使用的变量"""
        if var_name in self.defined_names:
            line, column, scope = self.defined_names[var_name]
            
            # 忽略常见的循环变量
            if var_name in ['i', 'j', 'k', 'index', 'idx', 'item'] and scope == "for_loop":
                return
            
            # 忽略下划线变量
            if var_name.startswith('_'):
                return
            
            issue = CodeIssue(
                issue_type=IssueType.UNUSED_VARIABLE,
                message=f"未使用的变量 '{var_name}'",
                line=line,
                column=column,
                node_name=var_name,
                details={"scope": scope}
            )
            self.results.add_issue(issue)
    
    def _record_name_usage(self, name: str):
        """记录名称使用"""
        self.used_names.add(name)
    
    def _record_name_definition(self, name: str, node: ast.AST):
        """记录名称定义"""
        if isinstance(node, ast.AST) and hasattr(node, 'lineno'):
            self.defined_names[name] = (node.lineno, node.col_offset, self.current_scope_name)
        
        # 将变量添加到当前作用域
        if self.scope_stack:
            self.scope_stack[-1].add(name)
    
    def _check_function_length(self, node: ast.FunctionDef):
        """检查函数长度"""
        # 获取函数结束行
        if not node.body:
            return
        
        # 计算函数体行数
        start_line = node.lineno
        end_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else start_line
        
        function_length = end_line - start_line
        
        if function_length > self.max_function_length:
            issue = CodeIssue(
                issue_type=IssueType.LONG_FUNCTION,
                message=f"函数 '{node.name}' 过长 ({function_length} 行，超过 {self.max_function_length} 行限制)",
                line=start_line,
                column=node.col_offset,
                node_name=node.name,
                details={
                    "function_length": function_length,
                    "max_allowed": self.max_function_length
                }
            )
            self.results.add_issue(issue)
    
    def _check_nesting_depth(self, node: ast.AST):
        """检查嵌套深度"""
        if self.nesting_depth > self.max_nesting_depth:
            issue = CodeIssue(
                issue_type=IssueType.DEEP_NESTING,
                message=f"嵌套过深 (深度: {self.nesting_depth}，超过 {self.max_nesting_depth} 层限制)",
                line=node.lineno if hasattr(node, 'lineno') else 0,
                column=node.col_offset if hasattr(node, 'col_offset') else 0,
                details={"current_depth": self.nesting_depth, "max_allowed": self.max_nesting_depth}
            )
            self.results.add_issue(issue)
    
    # 访问AST节点的方法
    def visit_Import(self, node: ast.Import):
        """处理import语句"""
        for alias in node.names:
            self.imports[alias.name] = (node.lineno, node.col_offset)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """处理from ... import语句"""
        module_name = node.module or ""
        
        for alias in node.names:
            full_name = f"{module_name}.{alias.name}" if module_name else alias.name
            self.imports[full_name] = (node.lineno, node.col_offset)
        
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """处理名称引用"""
        self._record_name_usage(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """处理函数定义"""
        # 记录函数名定义
        self._record_name_definition(node.name, node)
        
        # 进入函数作用域
        self._enter_scope(f"function:{node.name}")
        self.current_function = node
        self.function_start_line = node.lineno
        
        # 处理参数
        for arg in node.args.args:
            self._record_name_definition(arg.arg, arg)
        
        # 处理函数体
        self.generic_visit(node)
        
        # 检查函数长度
        self._check_function_length(node)
        
        # 退出函数作用域
        self._exit_scope()
        self.current_function = None
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """处理异步函数定义"""
        self.visit_FunctionDef(node)  # 复用函数逻辑
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """处理类定义"""
        self._record_name_definition(node.name, node)
        
        # 进入类作用域
        self._enter_scope(f"class:{node.name}")
        
        # 处理类体
        self.generic_visit(node)
        
        # 退出类作用域
        self._exit_scope()
    
    def visit_Assign(self, node: ast.Assign):
        """处理赋值语句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._record_name_definition(target.id, target)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self._record_name_definition(elt.id, elt)
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        """处理for循环"""
        # 记录循环变量
        if isinstance(node.target, ast.Name):
            self._record_name_definition(node.target.id, node.target)
            # 标记为循环变量作用域
            self.defined_names[node.target.id] = (node.target.lineno, node.target.col_offset, "for_loop")
        
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 处理循环体和else部分
        self.generic_visit(node)
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_While(self, node: ast.While):
        """处理while循环"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 处理循环体和else部分
        self.generic_visit(node)
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_If(self, node: ast.If):
        """处理if语句"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 处理if条件、then部分和else部分
        self.generic_visit(node)
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_Try(self, node: ast.Try):
        """处理try语句"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 处理try块、except块、else块和finally块
        self.generic_visit(node)
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_With(self, node: ast.With):
        """处理with语句"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 处理with项和with块
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                self._record_name_definition(item.optional_vars.id, item.optional_vars)
        
        self.generic_visit(node)
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_ListComp(self, node: ast.ListComp):
        """处理列表推导式"""
        self._visit_comprehension(node, "list_comprehension")
    
    def visit_SetComp(self, node: ast.SetComp):
        """处理集合推导式"""
        self._visit_comprehension(node, "set_comprehension")
    
    def visit_DictComp(self, node: ast.DictComp):
        """处理字典推导式"""
        self._visit_comprehension(node, "dict_comprehension")
    
    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """处理生成器表达式"""
        self._visit_comprehension(node, "generator_expression")
    
    def _visit_comprehension(self, node: ast.AST, comp_type: str):
        """处理推导式通用逻辑"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 进入推导式作用域
        self._enter_scope(comp_type)
        
        # 处理推导式的生成器
        self.generic_visit(node)
        
        # 退出推导式作用域
        self._exit_scope()
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def visit_Lambda(self, node: ast.Lambda):
        """处理lambda表达式"""
        # 增加嵌套深度
        self.nesting_depth += 1
        self._check_nesting_depth(node)
        
        # 进入lambda作用域
        self._enter_scope("lambda")
        
        # 处理参数
        for arg in node.args.args:
            self._record_name_definition(arg.arg, arg)
        
        # 处理lambda体
        self.generic_visit(node)
        
        # 退出lambda作用域
        self._exit_scope()
        
        # 减少嵌套深度
        self.nesting_depth -= 1
    
    def generic_visit(self, node: ast.AST):
        """通用访问方法"""
        # 记录当前最大嵌套深度
        if self.nesting_depth > self.max_current_nesting:
            self.max_current_nesting = self.nesting_depth
        
        super().generic_visit(node)
    
    def finalize(self):
        """完成检查，报告未使用的import"""
        # 检查未使用的import
        for import_name, (line, column) in self.imports.items():
            # 检查是否被使用
            used = False
            
            # 检查完整import名
            if import_name in self.used_names:
                used = True
            
            # 检查部分import名（如from module import func）
            if not used:
                parts = import_name.split('.')
                for i in range(1, len(parts) + 1):
                    partial_name = '.'.join(parts[:i])
                    if partial_name in self.used_names:
                        used = True
                        break
            
            # 检查通配符import（如from module import *）
            if not used and import_name.endswith('.*'):
                base_module = import_name[:-2]
                for used_name in self.used_names:
                    if used_name.startswith(base_module + '.') or used_name == base_module:
                        used = True
                        break
            
            if not used:
                issue = CodeIssue(
                    issue_type=IssueType.UNUSED_IMPORT,
                    message=f"未使用的导入 '{import_name}'",
                    line=line,
                    column=column,
                    node_name=import_name
                )
                self.results.add_issue(issue)
        
        # 添加总结信息
        self.results.summary = {
            "total_lines_analyzed": self._estimate_lines_analyzed(),
            "max_nesting_depth_found": self.max_current_nesting,
            "total_imports": len(self.imports),
            "total_definitions": len(self.defined_names),
            "total_used_names": len(self.used_names)
        }

    def _estimate_lines_analyzed(self) -> int:
        """估计分析的代码行数"""
        # 简单实现：返回最大行号
        max_line = 0
        for node_info in list(self.imports.values()) + list(self.defined_names.values()):
            if isinstance(node_info, tuple) and len(node_info) >= 1:
                max_line = max(max_line, node_info[0])
        return max_line

def check_code(source_code: str, **kwargs) -> CheckResults:
    """
    检查代码
    
    Args:
        source_code: 源代码字符串
        **kwargs: 传递给CodeCheckerVisitor的配置参数
    
    Returns:
        CheckResults: 检查结果
    """
    try:
        # 解析AST
        tree = ast.parse(source_code)
        
        # 创建访问器并检查
        visitor = CodeCheckerVisitor(**kwargs)
        visitor.visit(tree)
        visitor.finalize()
        
        return visitor.results
        
    except SyntaxError as e:
        # 处理语法错误
        results = CheckResults()
        results.add_issue(CodeIssue(
            issue_type=IssueType.UNUSED_IMPORT,  # 使用现有类型，尽管不是完全准确
            message=f"语法错误: {e.msg}",
            line=e.lineno,
            column=e.offset or 0,
            details={"syntax_error": True}
        ))
        return results

def check_file(file_path: str, **kwargs) -> CheckResults:
    """
    检查文件中的代码
    
    Args:
        file_path: 文件路径
        **kwargs: 传递给check_code的配置参数
    
    Returns:
        CheckResults: 检查结果
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        return check_code(source_code, **kwargs)
        
    except FileNotFoundError:
        results = CheckResults()
        results.add_issue(CodeIssue(
            issue_type=IssueType.UNUSED_IMPORT,
            message=f"文件不存在: {file_path}",
            line=0,
            column=0,
            details={"file_error": True}
        ))
        return results
    except UnicodeDecodeError:
        results = CheckResults()
        results.add_issue(CodeIssue(
            issue_type=IssueType.UNUSED_IMPORT,
            message=f"无法解码文件: {file_path} (请使用UTF-8编码)",
            line=0,
            column=0,
            details={"encoding_error": True}
        ))
        return results

# 示例代码用于测试
EXAMPLE_CODE = '''
import os
import sys
from collections import defaultdict
import json  # 未使用的导入

def long_function():
    """这是一个过长的函数示例"""
    x = 1
    y = 2
    z = 3  # 未使用的变量
    
    # 多层嵌套示例
    for i in range(10):
        if i % 2 == 0:
            for j in range(5):
                if j % 2 == 0:
                    for k in range(3):
                        if k % 2 == 0:
                            print("深度嵌套")
    
    unused_var = 100  # 未使用的变量
    
    return x + y

def short_function():
    return 42

class MyClass:
    def method_with_unused_var(self):
        unused = "not used"  # 未使用的类方法变量
        return self

# 使用一些导入
print(os.path.join("a", "b"))
data = defaultdict(list)
'''

def main():
    """主函数：示例和测试"""
    
    print("AST代码检查器示例")
    print("=" * 70)
    
    # 检查示例代码
    results = check_code(EXAMPLE_CODE, max_function_length=20, max_nesting_depth=3)
    
    # 输出结果
    print("检查结果:")
    print(f"总问题数: {results.get_issue_count()}")
    
    summary = results.get_issue_summary()
    for issue_type, count in summary.items():
        print(f"  {issue_type.value}: {count}")
    
    print("\n详细问题:")
    for issue in results.issues:
        print(f"  [{issue.issue_type.value}] 第{issue.line}行: {issue.message}")
        if issue.details:
            print(f"      详情: {issue.details}")
    
    print(f"\n总结信息: {results.summary}")
    
    # 转换为字典格式
    print("\n字典格式输出:")
    result_dict = results.to_dict()
    import json
    print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    
    # 演示不同配置
    print("\n" + "=" * 70)
    print("使用不同配置的检查:")
    
    # 更宽松的配置
    lax_results = check_code(EXAMPLE_CODE, max_function_length=100, max_nesting_depth=10)
    print(f"宽松配置 - 问题数: {lax_results.get_issue_count()}")
    
    # 更严格的配置
    strict_results = check_code(EXAMPLE_CODE, max_function_length=10, max_nesting_depth=2)
    print(f"严格配置 - 问题数: {strict_results.get_issue_count()}")
    
    # 测试错误处理
    print("\n" + "=" * 70)
    print("错误处理测试:")
    
    invalid_code = '''
    def invalid_syntax(
        missing_paren  # 缺少右括号
    '''
    
    error_results = check_code(invalid_code)
    if error_results.issues:
        print(f"语法错误检测: {error_results.issues[0].message}")

if __name__ == "__main__":
    main()