"""
MC-PY-04: Python Code Checker
Engineering Constraints: Python 3.10+, stdlib only. ast.NodeVisitor required, no regex.
Results as dataclass. Full type annotations. Check: unused import/var, long func, deep nest.
Single file, class output.
"""

from __future__ import annotations

import ast
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# ── Result Dataclasses ──────────────────────────────────────────────────


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    UNUSED_IMPORT = "unused_import"
    UNUSED_VARIABLE = "unused_variable"
    LONG_FUNCTION = "long_function"
    DEEP_NESTING = "deep_nesting"


@dataclass
class CodeIssue:
    issue_type: IssueType
    message: str
    lineno: int
    col_offset: int = 0
    severity: IssueSeverity = IssueSeverity.WARNING
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.issue_type.value,
            "message": self.message,
            "line": self.lineno,
            "col": self.col_offset,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
        }

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] line {self.lineno}: {self.message}"


@dataclass
class ImportInfo:
    module_name: str
    alias: Optional[str] = None
    lineno: int = 0
    is_used: bool = False
    import_type: str = "import"

    def to_dict(self) -> Dict[str, Any]:
        return {"module": self.module_name, "alias": self.alias, "line": self.lineno, "used": self.is_used, "type": self.import_type}


@dataclass
class VariableInfo:
    name: str
    var_type: str = "variable"
    defined_at: int = 0
    is_used: bool = False
    scope_function: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.var_type, "line": self.defined_at, "used": self.is_used, "scope": self.scope_function}


@dataclass
class FunctionInfo:
    name: str
    start_line: int = 0
    end_line: int = 0
    line_count: int = 0
    args_count: int = 0
    max_nesting: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "start": self.start_line, "end": self.end_line, "lines": self.line_count, "args": self.args_count, "nesting": self.max_nesting}


@dataclass
class CodeAnalysisResult:
    source_file: str
    issues: List[CodeIssue] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    variables: List[VariableInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    max_nesting_depth: int = 0
    analysis_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.source_file,
            "success": self.success,
            "error": self.error_message,
            "time": self.analysis_time,
            "summary": {
                "total_issues": len(self.issues),
                "unused_imports": sum(1 for i in self.imports if not i.is_used),
                "unused_variables": sum(1 for v in self.variables if not v.is_used and v.var_type == "variable"),
                "long_functions": sum(1 for f in self.functions if f.line_count > 50),
                "max_nesting": self.max_nesting_depth,
            },
            "issues": [i.to_dict() for i in self.issues],
            "imports": [i.to_dict() for i in self.imports],
            "variables": [v.to_dict() for v in self.variables],
            "functions": [f.to_dict() for f in self.functions],
        }

    def has_errors(self) -> bool:
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    def format_text(self) -> str:
        lines: List[str] = [f"Code Analysis: {self.source_file}", "=" * 50]
        summary = self.to_dict()["summary"]
        lines.append(f"Issues: {summary['total_issues']}  |  Unused imports: {summary['unused_imports']}  |  "
                      f"Unused vars: {summary['unused_variables']}  |  Long funcs: {summary['long_functions']}  |  "
                      f"Max nesting: {summary['max_nesting']}")
        if self.issues:
            lines.append("\nIssues:")
            for issue in sorted(self.issues, key=lambda x: x.lineno):
                lines.append(f"  {issue}")
                if issue.suggestion:
                    lines.append(f"    -> {issue.suggestion}")
        return "\n".join(lines)


# ── Import Collector ────────────────────────────────────────────────────


class ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: Dict[str, ImportInfo] = {}
        self.import_names: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[-1]
            self.imports[name] = ImportInfo(
                module_name=alias.name,
                alias=alias.asname,
                lineno=node.lineno,
                import_type="import",
            )
            self.import_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            full = f"{module}.{alias.name}" if module else alias.name
            self.imports[name] = ImportInfo(
                module_name=full,
                alias=alias.asname,
                lineno=node.lineno,
                import_type="from_import",
            )
            self.import_names.add(name)
        self.generic_visit(node)


# ── Name Usage Tracker ──────────────────────────────────────────────────


class NameUsageTracker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.used_names: Set[str] = set()
        self.defined_vars: Dict[str, VariableInfo] = {}
        self._current_func: Optional[str] = None
        self._in_definition: bool = False
        # Names that shouldn't be flagged
        self._builtins = {"__name__", "__file__", "__doc__", "__all__", "_", "self", "cls"}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old = self._current_func
        self._current_func = node.name
        self.used_names.add(node.name)  # Function name is "used" by definition
        # Record params
        for arg in node.args.args:
            if arg.arg not in self._builtins:
                self.defined_vars.setdefault(arg.arg, VariableInfo(
                    name=arg.arg, var_type="parameter", defined_at=node.lineno, scope_function=node.name
                ))
        self.generic_visit(node)
        self._current_func = old

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.used_names.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if node.id not in self._builtins:
                self.defined_vars.setdefault(node.id, VariableInfo(
                    name=node.id, var_type="variable", defined_at=node.lineno, scope_function=self._current_func
                ))
        elif isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_Decorator(self, node: ast.AST) -> None:
        # Decorators count as usage
        self.generic_visit(node)


# ── Function Analyzer ───────────────────────────────────────────────────


class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self, max_lines: int = 50) -> None:
        self.functions: List[FunctionInfo] = []
        self.issues: List[CodeIssue] = []
        self.max_lines = max_lines

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        end = node.end_lineno or node.lineno
        count = end - node.lineno + 1
        info = FunctionInfo(
            name=node.name,
            start_line=node.lineno,
            end_line=end,
            line_count=count,
            args_count=len(node.args.args),
        )
        self.functions.append(info)

        if count > self.max_lines:
            self.issues.append(CodeIssue(
                issue_type=IssueType.LONG_FUNCTION,
                message=f"Function '{node.name}' is {count} lines (max {self.max_lines})",
                lineno=node.lineno,
                col_offset=node.col_offset,
                suggestion=f"Consider splitting '{node.name}' into smaller functions",
            ))

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]


# ── Nesting Analyzer ───────────────────────────────────────────────────


class NestingAnalyzer(ast.NodeVisitor):
    def __init__(self, max_depth: int = 4) -> None:
        self.max_depth = max_depth
        self.issues: List[CodeIssue] = []
        self.global_max: int = 0
        self._depth: int = 0
        self._func_name: Optional[str] = None
        self._func_max: Dict[str, int] = {}

    def _enter(self, node: ast.AST) -> None:
        self._depth += 1
        if self._depth > self.global_max:
            self.global_max = self._depth

    def _exit(self) -> None:
        self._depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_func = self._func_name
        old_depth = self._depth
        self._func_name = node.name
        self._depth = 0  # Reset for function scope
        self.generic_visit(node)
        func_max = self._depth  # Should be 0 after generic_visit pops, track via max

        self._func_name = old_func
        self._depth = old_depth

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_If(self, node: ast.If) -> None:
        self._enter(node)
        self._check_depth(node)
        self.generic_visit(node)
        self._exit()

    def visit_For(self, node: ast.For) -> None:
        self._enter(node)
        self._check_depth(node)
        self.generic_visit(node)
        self._exit()

    def visit_While(self, node: ast.While) -> None:
        self._enter(node)
        self._check_depth(node)
        self.generic_visit(node)
        self._exit()

    def visit_Try(self, node: ast.Try) -> None:
        self._enter(node)
        self._check_depth(node)
        self.generic_visit(node)
        self._exit()

    def visit_With(self, node: ast.With) -> None:
        self._enter(node)
        self._check_depth(node)
        self.generic_visit(node)
        self._exit()

    def _check_depth(self, node: ast.AST) -> None:
        if self._depth > self.max_depth:
            lineno = getattr(node, "lineno", 0)
            loc = f" in '{self._func_name}'" if self._func_name else ""
            self.issues.append(CodeIssue(
                issue_type=IssueType.DEEP_NESTING,
                message=f"Nesting depth {self._depth} exceeds max {self.max_depth}{loc}",
                lineno=lineno,
                severity=IssueSeverity.WARNING,
                suggestion="Reduce nesting with early returns, guard clauses, or extract helper functions",
            ))


# ── Main Checker ────────────────────────────────────────────────────────


class CodeChecker:
    def __init__(
        self,
        max_function_lines: int = 50,
        max_nesting_depth: int = 4,
    ) -> None:
        self.max_function_lines = max_function_lines
        self.max_nesting_depth = max_nesting_depth

    def check(self, source_code: str, filename: str = "<string>") -> CodeAnalysisResult:
        start = time.time()
        result = CodeAnalysisResult(source_file=filename)

        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            result.success = False
            result.error_message = f"Syntax error: {e}"
            result.analysis_time = time.time() - start
            return result

        # 1. Collect imports
        import_collector = ImportCollector()
        import_collector.visit(tree)

        # 2. Track name usage
        name_tracker = NameUsageTracker()
        name_tracker.visit(tree)

        # 3. Function analysis
        func_analyzer = FunctionAnalyzer(self.max_function_lines)
        func_analyzer.visit(tree)

        # 4. Nesting analysis
        nesting_analyzer = NestingAnalyzer(self.max_nesting_depth)
        nesting_analyzer.visit(tree)

        # ── Compute unused imports ──
        for name, imp in import_collector.imports.items():
            if name in name_tracker.used_names:
                imp.is_used = True
            result.imports.append(imp)
            if not imp.is_used:
                result.issues.append(CodeIssue(
                    issue_type=IssueType.UNUSED_IMPORT,
                    message=f"Unused import: '{name}' ({imp.module_name})",
                    lineno=imp.lineno,
                    severity=IssueSeverity.WARNING,
                    suggestion=f"Remove 'import {imp.module_name}' or use '{name}' in your code",
                ))

        # ── Compute unused variables ──
        for name, var in name_tracker.defined_vars.items():
            if name in name_tracker.used_names or name in import_collector.import_names:
                var.is_used = True
            # Skip parameters named 'self' / 'cls' / underscore-prefixed
            if name.startswith("_") or var.var_type == "parameter":
                var.is_used = True
            result.variables.append(var)
            if not var.is_used:
                result.issues.append(CodeIssue(
                    issue_type=IssueType.UNUSED_VARIABLE,
                    message=f"Unused variable: '{name}'",
                    lineno=var.defined_at,
                    severity=IssueSeverity.WARNING,
                    suggestion=f"Remove variable '{name}' or prefix with '_' if intentionally unused",
                ))

        # ── Merge function & nesting results ──
        result.functions = func_analyzer.functions
        result.issues.extend(func_analyzer.issues)
        result.issues.extend(nesting_analyzer.issues)
        result.max_nesting_depth = nesting_analyzer.global_max

        result.analysis_time = time.time() - start
        return result

    def check_file(self, filepath: str) -> CodeAnalysisResult:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            result = CodeAnalysisResult(source_file=filepath, success=False, error_message=f"File not found: {filepath}")
            return result
        except IOError as e:
            result = CodeAnalysisResult(source_file=filepath, success=False, error_message=str(e))
            return result
        return self.check(source, filepath)


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = '''
import os
import sys
import json
from collections import defaultdict

CONSTANT = 42
unused_global = "never used"

def short_function(x, y):
    return x + y

def long_function(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                for sub in range(item):
                    if sub > 5:
                        if sub % 3 == 0:
                            try:
                                val = item * sub
                                result.append(val)
                            except Exception:
                                pass
    return result

class MyClass:
    def __init__(self):
        self.value = 10
        temp = 20

    def process(self):
        data = json.loads("{}")
        return data
'''

    checker = CodeChecker(max_function_lines=50, max_nesting_depth=4)
    result = checker.check(sample_code, "sample.py")
    print(result.format_text())
    print("\n--- JSON ---")
    print(json.dumps(result.to_dict(), indent=2))
