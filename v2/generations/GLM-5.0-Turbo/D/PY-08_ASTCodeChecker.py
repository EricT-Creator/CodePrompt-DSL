"""
AST代码检查器 - 使用ast模块和NodeVisitor
检测未使用的import/变量、过长函数、过深嵌套
"""

import ast
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CheckIssue:
    line: int
    col: int
    severity: str
    category: str
    message: str

    def __str__(self):
        return f"行 {self.line}:{self.col} [{self.severity}] {self.category}: {self.message}"


@dataclass
class CheckResults:
    issues: list = field(default_factory=list)

    @property
    def unused_imports(self) -> list:
        return [i for i in self.issues if i.category == "unused_import"]

    @property
    def unused_variables(self) -> list:
        return [i for i in self.issues if i.category == "unused_variable"]

    @property
    def long_functions(self) -> list:
        return [i for i in self.issues if i.category == "long_function"]

    @property
    def deep_nesting(self) -> list:
        return [i for i in self.issues if i.category == "deep_nesting"]

    @property
    def total(self) -> int:
        return len(self.issues)

    def summary(self) -> str:
        parts = [f"共发现 {self.total} 个问题:"]
        counts = {}
        for issue in self.issues:
            counts[issue.category] = counts.get(issue.category, 0) + 1
        for cat, count in sorted(counts.items()):
            parts.append(f"  {cat}: {count}")
        return "\n".join(parts)


class _ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imports: dict[str, tuple[int, int]] = {}

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports[name] = (node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = (node.lineno, node.col_offset)
        self.generic_visit(node)


class _NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.names: set[str] = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Load):
            if isinstance(node.value, ast.Name):
                self.names.add(node.value.id)
        self.generic_visit(node)


class _VariableCollector(ast.NodeVisitor):
    def __init__(self):
        self.variables: set[str] = set()

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.variables.add(node.target.id)
        self.generic_visit(node)


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, max_lines: int = 50):
        self.max_lines = max_lines
        self.long_functions: list = []

    def _get_func_length(self, node) -> int:
        if not hasattr(node, "end_lineno") or node.end_lineno is None:
            return 0
        return node.end_lineno - node.lineno + 1

    def visit_FunctionDef(self, node):
        length = self._get_func_length(node)
        if length > self.max_lines:
            self.long_functions.append({
                "name": node.name,
                "line": node.lineno,
                "length": length,
            })
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class _NestingCollector(ast.NodeVisitor):
    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.deep_nesting: list = []
        self._current_depth = 0

    def _enter_block(self, node):
        self._current_depth += 1
        if self._current_depth > self.max_depth:
            self.deep_nesting.append({
                "line": node.lineno,
                "depth": self._current_depth,
                "type": type(node).__name__,
            })
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_If(self, node):
        self._enter_block(node)

    def visit_For(self, node):
        self._enter_block(node)

    visit_AsyncFor = visit_For

    def visit_While(self, node):
        self._enter_block(node)

    def visit_With(self, node):
        self._enter_block(node)

    visit_AsyncWith = visit_With

    def visit_Try(self, node):
        self._enter_block(node)

    def visit_TryStar(self, node):
        self._enter_block(node)

    def visit_ExceptHandler(self, node):
        self._enter_block(node)


class _AugAssignCollector(ast.NodeVisitor):
    def __init__(self):
        self.aug_assign_targets: set[str] = set()

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.aug_assign_targets.add(node.target.id)
        self.generic_visit(node)


class _FunctionParamCollector(ast.NodeVisitor):
    def __init__(self):
        self.params: set[str] = set()

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            self.params.add(arg.arg)
        if node.args.vararg:
            self.params.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.params.add(node.args.kwarg.arg)
        for arg in node.args.kwonlyargs:
            self.params.add(arg.arg)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class _ForLoopVarCollector(ast.NodeVisitor):
    def __init__(self):
        self.loop_vars: set[str] = set()

    def visit_For(self, node):
        if isinstance(node.target, ast.Name):
            self.loop_vars.add(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in ast.walk(node.target):
                if isinstance(elt, ast.Name):
                    self.loop_vars.add(elt.id)
        self.generic_visit(node)

    visit_AsyncFor = visit_For


def check_code(source: str) -> CheckResults:
    results = CheckResults()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        results.issues.append(CheckIssue(
            line=e.lineno or 1,
            col=e.offset or 0,
            severity="error",
            category="syntax_error",
            message=f"语法错误: {e.msg}",
        ))
        return results

    # 检查未使用的import
    import_collector = _ImportCollector()
    import_collector.visit(tree)

    name_collector = _NameCollector()
    name_collector.visit(tree)

    unused_names = set(import_collector.imports.keys()) - name_collector.names
    for name in sorted(unused_names):
        line, col = import_collector.imports[name]
        results.issues.append(CheckIssue(
            line=line, col=col,
            severity="warning",
            category="unused_import",
            message=f"未使用的导入: {name}",
        ))

    # 检查未使用的变量
    var_collector = _VariableCollector()
    var_collector.visit(tree)

    aug_collector = _AugAssignCollector()
    aug_collector.visit(tree)

    param_collector = _FunctionParamCollector()
    param_collector.visit(tree)

    loop_var_collector = _ForLoopVarCollector()
    loop_var_collector.visit(tree)

    builtin_names = {
        "print", "len", "range", "str", "int", "float", "list", "dict",
        "set", "tuple", "bool", "type", "isinstance", "hasattr", "getattr",
        "setattr", "delattr", "super", "property", "classmethod", "staticmethod",
        "enumerate", "zip", "map", "filter", "sorted", "reversed", "min",
        "max", "sum", "abs", "round", "input", "open", "format", "repr",
        "id", "hash", "dir", "vars", "globals", "locals", "exec", "eval",
        "compile", "__name__", "__file__", "__doc__", "True", "False", "None",
    }

    all_vars = var_collector.variables | aug_collector.aug_assign_targets
    exclude = builtin_names | param_collector.params | loop_var_collector.loop_vars
    candidates = all_vars - exclude

    for var in candidates:
        if var not in name_collector.names:
            node = _find_var_node(tree, var)
            if node:
                results.issues.append(CheckIssue(
                    line=node.lineno,
                    col=node.col_offset,
                    severity="info",
                    category="unused_variable",
                    message=f"变量已赋值但未使用: {var}",
                ))

    # 检查过长函数 (>50行)
    func_collector = _FunctionCollector(max_lines=50)
    func_collector.visit(tree)
    for func in func_collector.long_functions:
        results.issues.append(CheckIssue(
            line=func["line"], col=0,
            severity="warning",
            category="long_function",
            message=f"函数 '{func['name']}' 过长: {func['length']} 行 (上限 50 行)",
        ))

    # 检查过深嵌套 (>4层)
    nesting_collector = _NestingCollector(max_depth=4)
    nesting_collector.visit(tree)
    for nest in nesting_collector.deep_nesting:
        results.issues.append(CheckIssue(
            line=nest["line"], col=0,
            severity="info",
            category="deep_nesting",
            message=f"嵌套层级过深: {nest['depth']} 层 (在 {nest['type']} 处, 上限 4 层)",
        ))

    return results


def _find_var_node(tree: ast.Module, var_name: str) -> Optional[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    return node
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == var_name:
                return node
    return None


def main():
    sample_code = '''
import os
import sys
import json
import collections

def process_data(items, filter_key):
    result = []
    for item in items:
        if item is not None:
            if filter_key in item:
                if item[filter_key] > 0:
                    for sub in item["children"]:
                        if sub:
                            unused_var = 42
                            result.append(sub)
    return result

def very_long_function(x, y):
    a = x + y
    b = a * 2
    c = b - 1
    d = c + 3
    e = d * 4
    f = e - 2
    g = f + 5
    h = g * 6
    i = h - 3
    j = i + 7
    k = j * 8
    l = k - 4
    m = l + 9
    n = m * 10
    o = n - 5
    p = o + 11
    q = p * 12
    r = q - 6
    s = r + 13
    t = s * 14
    u = t - 7
    v = u + 15
    w = v * 16
    xx = w - 8
    yy = xx + 17
    zz = yy * 18
    aaa = zz - 9
    bbb = aaa + 19
    ccc = bbb * 20
    ddd = ccc - 10
    eee = ddd + 21
    fff = eee * 22
    ggg = fff - 11
    hhh = ggg + 23
    iii = hhh * 24
    jjj = iii - 12
    kkk = jjj + 25
    lll = kkk * 26
    mmm = lll - 13
    nnn = mmm + 27
    ooo = nnn * 28
    ppp = ooo - 14
    qqq = ppp + 29
    return qqq
'''

    results = check_code(sample_code)
    print(results.summary())
    print()
    for issue in results.issues:
        print(f"  {issue}")
    return results


if __name__ == "__main__":
    main()
