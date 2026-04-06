import ast
import builtins
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
import inspect

# Issue severity levels
class Severity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

# Issue types
class IssueType(Enum):
    UNUSED_IMPORT = "UNUSED_IMPORT"
    UNUSED_VARIABLE = "UNUSED_VARIABLE"
    LONG_FUNCTION = "LONG_FUNCTION"
    DEEP_NESTING = "DEEP_NESTING"
    UNUSED_FUNCTION = "UNUSED_FUNCTION"
    UNUSED_CLASS = "UNUSED_CLASS"

@dataclass
class CodeIssue:
    type: IssueType
    severity: Severity
    message: str
    line: int
    column: int
    name: Optional[str] = None
    extra_info: Optional[Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "name": self.name,
            "extra_info": self.extra_info
        }

@dataclass
class CheckResults:
    issues: List[CodeIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def add_issue(self, issue: CodeIssue):
        self.issues.append(issue)
        issue_type = issue.type.value
        self.summary[issue_type] = self.summary.get(issue_type, 0) + 1
    
    def to_dict(self) -> Dict:
        return {
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": self.summary,
            "total_issues": len(self.issues)
        }
    
    def get_issues_by_type(self, issue_type: IssueType) -> List[CodeIssue]:
        return [issue for issue in self.issues if issue.type == issue_type]
    
    def get_issues_by_severity(self, severity: Severity) -> List[CodeIssue]:
        return [issue for issue in self.issues if issue.severity == severity]

# Symbol usage tracker
class SymbolTracker:
    """Tracks symbol definitions and usages."""
    
    def __init__(self):
        self.imports: Dict[str, Set[str]] = {}  # module -> set of imported names
        self.variables: Dict[str, List[Tuple[int, int]]] = {}  # name -> list of (line, col) definitions
        self.usages: Set[str] = set()  # names that are used
        self.functions: Dict[str, List[Tuple[int, int]]] = {}  # function name -> list of definitions
        self.classes: Dict[str, List[Tuple[int, int]]] = {}  # class name -> list of definitions
        self.current_scope: List[str] = []  # stack of current scopes
        
    def add_import(self, module: str, name: str, line: int, col: int):
        """Record an import."""
        if module not in self.imports:
            self.imports[module] = set()
        self.imports[module].add(name)
        # Record the imported name as a variable definition
        self.add_variable(name, line, col)
    
    def add_variable(self, name: str, line: int, col: int):
        """Record a variable definition."""
        if name not in self.variables:
            self.variables[name] = []
        self.variables[name].append((line, col))
    
    def mark_usage(self, name: str):
        """Mark a symbol as used."""
        self.usages.add(name)
    
    def add_function(self, name: str, line: int, col: int):
        """Record a function definition."""
        if name not in self.functions:
            self.functions[name] = []
        self.functions[name].append((line, col))
        # Also record as a variable in current scope
        self.add_variable(name, line, col)
    
    def add_class(self, name: str, line: int, col: int):
        """Record a class definition."""
        if name not in self.classes:
            self.classes[name] = []
        self.classes[name].append((line, col))
        # Also record as a variable in current scope
        self.add_variable(name, line, col)
    
    def push_scope(self, name: str):
        """Enter a new scope."""
        self.current_scope.append(name)
    
    def pop_scope(self):
        """Exit the current scope."""
        if self.current_scope:
            self.current_scope.pop()
    
    def get_unused_variables(self) -> List[Tuple[str, Tuple[int, int]]]:
        """Get list of unused variables with their locations."""
        unused = []
        for name, locations in self.variables.items():
            if name not in self.usages and name not in dir(builtins):
                for line, col in locations:
                    unused.append((name, (line, col)))
        return unused
    
    def get_unused_imports(self) -> List[Tuple[str, str, Tuple[int, int]]]:
        """Get list of unused imports."""
        unused = []
        for module, names in self.imports.items():
            for name in names:
                if name not in self.usages:
                    # Find the location of this import
                    # For simplicity, we'll use the first variable definition location
                    if name in self.variables:
                        for line, col in self.variables[name]:
                            unused.append((module, name, (line, col)))
                            break
        return unused

# AST Visitor for code analysis
class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor that analyzes Python code for various issues."""
    
    def __init__(self):
        self.tracker = SymbolTracker()
        self.issues: List[CodeIssue] = []
        self.function_line_counts: Dict[str, int] = {}
        self.nesting_depth: int = 0
        self.max_nesting_depth: int = 0
        self.current_function: Optional[str] = None
        
    def visit_Import(self, node: ast.Import):
        """Visit import statements."""
        for alias in node.names:
            if alias.asname:
                # import module as alias
                self.tracker.add_import(alias.name, alias.asname, node.lineno, node.col_offset)
            else:
                # import module
                # For simplicity, we'll treat the module name as the imported symbol
                module_name = alias.name.split('.')[0]
                self.tracker.add_import(alias.name, module_name, node.lineno, node.col_offset)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from ... import statements."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.tracker.add_import(module, name, node.lineno, node.col_offset)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        self.tracker.add_function(node.name, node.lineno, node.col_offset)
        self.tracker.push_scope(node.name)
        
        # Store current function for line counting
        prev_function = self.current_function
        self.current_function = node.name
        
        # Calculate function length
        if node.body:
            start_line = node.lineno
            end_line = self._get_end_line(node)
            line_count = end_line - start_line + 1
            self.function_line_counts[node.name] = line_count
        
        # Visit function body with increased nesting
        prev_nesting = self.nesting_depth
        self.nesting_depth = 0
        self.max_nesting_depth = 0
        
        self.generic_visit(node)
        
        # Check for deep nesting in this function
        if self.max_nesting_depth > 4:
            self.issues.append(CodeIssue(
                type=IssueType.DEEP_NESTING,
                severity=Severity.WARNING,
                message=f"Function '{node.name}' has nesting depth of {self.max_nesting_depth} (max recommended: 4)",
                line=node.lineno,
                column=node.col_offset,
                name=node.name,
                extra_info={"depth": self.max_nesting_depth}
            ))
        
        # Check for long function
        if self.function_line_counts.get(node.name, 0) > 50:
            self.issues.append(CodeIssue(
                type=IssueType.LONG_FUNCTION,
                severity=Severity.WARNING,
                message=f"Function '{node.name}' is {self.function_line_counts[node.name]} lines long (max recommended: 50)",
                line=node.lineno,
                column=node.col_offset,
                name=node.name,
                extra_info={"line_count": self.function_line_counts[node.name]}
            ))
        
        self.nesting_depth = prev_nesting
        self.current_function = prev_function
        self.tracker.pop_scope()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definitions."""
        # Treat async functions the same as regular functions
        self.visit_FunctionDef(ast.FunctionDef(
            name=node.name,
            args=node.args,
            body=node.body,
            decorator_list=node.decorator_list,
            returns=node.returns,
            lineno=node.lineno,
            col_offset=node.col_offset
        ))
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        self.tracker.add_class(node.name, node.lineno, node.col_offset)
        self.tracker.push_scope(node.name)
        self.generic_visit(node)
        self.tracker.pop_scope()
    
    def visit_Assign(self, node: ast.Assign):
        """Visit assignment statements."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.tracker.add_variable(target.id, node.lineno, node.col_offset)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self.tracker.add_variable(elt.id, node.lineno, node.col_offset)
        
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit annotated assignment statements."""
        if isinstance(node.target, ast.Name):
            self.tracker.add_variable(node.target.id, node.lineno, node.col_offset)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Visit name nodes (variable references)."""
        if isinstance(node.ctx, (ast.Load, ast.AugLoad)):
            self.tracker.mark_usage(node.id)
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        """Visit for loops."""
        # Handle loop variable
        if isinstance(node.target, ast.Name):
            self.tracker.add_variable(node.target.id, node.lineno, node.col_offset)
        elif isinstance(node.target, ast.Tuple):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    self.tracker.add_variable(elt.id, node.lineno, node.col_offset)
        
        # Increase nesting depth
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.nesting_depth
        
        self.generic_visit(node)
        
        # Decrease nesting depth
        self.nesting_depth -= 1
    
    def visit_While(self, node: ast.While):
        """Visit while loops."""
        # Increase nesting depth
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.nesting_depth
        
        self.generic_visit(node)
        
        # Decrease nesting depth
        self.nesting_depth -= 1
    
    def visit_If(self, node: ast.If):
        """Visit if statements."""
        # Increase nesting depth
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.nesting_depth
        
        self.generic_visit(node)
        
        # Visit elif and else branches
        for elif_node in node.orelse:
            if isinstance(elif_node, ast.If):
                self.visit(elif_node)
            else:
                self.generic_visit(elif_node)
        
        # Decrease nesting depth
        self.nesting_depth -= 1
    
    def visit_Try(self, node: ast.Try):
        """Visit try statements."""
        # Increase nesting depth
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.nesting_depth
        
        # Visit try body
        for stmt in node.body:
            self.visit(stmt)
        
        # Visit except handlers
        for handler in node.handlers:
            if handler.name:
                self.tracker.add_variable(handler.name, handler.lineno, handler.col_offset)
            for stmt in handler.body:
                self.visit(stmt)
        
        # Visit else clause
        for stmt in node.orelse:
            self.visit(stmt)
        
        # Visit finally clause
        for stmt in node.finalbody:
            self.visit(stmt)
        
        # Decrease nesting depth
        self.nesting_depth -= 1
    
    def visit_With(self, node: ast.With):
        """Visit with statements."""
        # Increase nesting depth
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.max_nesting_depth
        
        # Handle optional asname
        for item in node.items:
            if item.optional_vars:
                if isinstance(item.optional_vars, ast.Name):
                    self.tracker.add_variable(item.optional_vars.id, node.lineno, node.col_offset)
                elif isinstance(item.optional_vars, ast.Tuple):
                    for elt in item.optional_vars.elts:
                        if isinstance(elt, ast.Name):
                            self.tracker.add_variable(elt.id, node.lineno, node.col_offset)
        
        self.generic_visit(node)
        
        # Decrease nesting depth
        self.nesting_depth -= 1
    
    def _get_end_line(self, node: ast.AST) -> int:
        """Get the end line of an AST node."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # Fallback: find the maximum line number in child nodes
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno:
                max_line = max(max_line, child.lineno)
        return max_line
    
    def collect_issues(self) -> List[CodeIssue]:
        """Collect all issues after analysis."""
        # Check for unused imports
        for module, name, (line, col) in self.tracker.get_unused_imports():
            self.issues.append(CodeIssue(
                type=IssueType.UNUSED_IMPORT,
                severity=Severity.WARNING,
                message=f"Unused import '{name}' from module '{module}'",
                line=line,
                column=col,
                name=name,
                extra_info={"module": module}
            ))
        
        # Check for unused variables
        for name, (line, col) in self.tracker.get_unused_variables():
            # Skip if it's a function or class name (handled separately)
            if name in self.tracker.functions or name in self.tracker.classes:
                continue
            
            self.issues.append(CodeIssue(
                type=IssueType.UNUSED_VARIABLE,
                severity=Severity.WARNING,
                message=f"Unused variable '{name}'",
                line=line,
                column=col,
                name=name
            ))
        
        # Sort issues by line number
        self.issues.sort(key=lambda x: x.line)
        
        return self.issues

# Main code checker
def check_code(source: str) -> CheckResults:
    """
    Analyze Python source code for various issues.
    
    Args:
        source: Python source code as a string
        
    Returns:
        CheckResults object containing all found issues
        
    Raises:
        SyntaxError: If the source code has syntax errors
    """
    try:
        # Parse the source code
        tree = ast.parse(source)
        
        # Analyze the AST
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        
        # Collect issues
        issues = analyzer.collect_issues()
        
        # Create results
        results = CheckResults()
        for issue in issues:
            results.add_issue(issue)
        
        return results
        
    except SyntaxError as e:
        # Re-raise syntax errors
        raise SyntaxError(f"Invalid Python syntax: {e}") from e
    except Exception as e:
        # Return an error issue for other exceptions
        results = CheckResults()
        results.add_issue(CodeIssue(
            type=IssueType.UNUSED_IMPORT,  # Using this as a generic error type
            severity=Severity.ERROR,
            message=f"Analysis failed: {str(e)}",
            line=1,
            column=1
        ))
        return results

# Utility functions
def print_results(results: CheckResults, verbose: bool = False):
    """Print check results in a readable format."""
    if not results.issues:
        print("✓ No issues found!")
        return
    
    print(f"Found {len(results.issues)} issue(s):")
    print("-" * 80)
    
    # Group issues by type
    issues_by_type: Dict[IssueType, List[CodeIssue]] = {}
    for issue in results.issues:
        if issue.type not in issues_by_type:
            issues_by_type[issue.type] = []
        issues_by_type[issue.type].append(issue)
    
    # Print by type
    for issue_type, issues in sorted(issues_by_type.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{issue_type.value}: {len(issues)} issue(s)")
        print("-" * 40)
        
        for issue in issues:
            print(f"  Line {issue.line}:{issue.column} - {issue.severity.value} - {issue.message}")
            if verbose and issue.extra_info:
                for key, value in issue.extra_info.items():
                    print(f"    {key}: {value}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    for issue_type, count in results.summary.items():
        print(f"  {issue_type}: {count}")
    print(f"  Total: {len(results.issues)}")

def analyze_file(filepath: str, verbose: bool = False) -> CheckResults:
    """Analyze a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        print(f"Analyzing {filepath}...")
        results = check_code(source)
        print_results(results, verbose)
        
        return results
        
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return CheckResults()
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return CheckResults()

# Example usage and testing
def example_usage():
    """Example usage of the code checker."""
    print("Python Code Checker Example")
    print("=" * 80)
    
    # Example code with various issues
    example_code = '''
import os
import sys
import json
from collections import defaultdict
import math  # Unused import

def long_function():
    """This function is too long."""
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    h = 8
    i = 9
    j = 10
    k = 11
    l = 12
    m = 13
    n = 14
    o = 15
    p = 16
    q = 17
    r = 18
    s = 19
    t = 20
    u = 21
    v = 22
    w = 23
    x = 24
    y = 25
    z = 26
    aa = 27
    bb = 28
    cc = 29
    dd = 30
    ee = 31
    ff = 32
    gg = 33
    hh = 34
    ii = 35
    jj = 36
    kk = 37
    ll = 38
    mm = 39
    nn = 40
    oo = 41
    pp = 42
    qq = 43
    rr = 44
    ss = 45
    tt = 46
    uu = 47
    vv = 48
    ww = 49
    xx = 50
    yy = 51  # Unused variable
    
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:  # Deep nesting
                        print("Too deep!")
    
    return a + b

def unused_function():
    """This function is never called."""
    x = 1
    y = 2  # Unused variable
    return x

class UnusedClass:
    """This class is never used."""
    pass

def complex_function(data):
    """Function with various constructs."""
    unused_var = 42  # Unused variable
    
    result = []
    for item in data:
        if item > 0:
            try:
                value = item * 2
                if value > 10:
                    result.append(value)
            except Exception:
                pass
    
    return result

# Main code
if __name__ == "__main__":
    data = [1, 2, 3, 4, 5]
    output = complex_function(data)
    print(f"Output: {output}")
    
    # Call the long function
    result = long_function()
    print(f"Long function result: {result}")
'''
    
    print("Analyzing example code...")
    print("-" * 80)
    
    results = check_code(example_code)
    print_results(results, verbose=True)
    
    # Show JSON output example
    print("\n" + "=" * 80)
    print("JSON Output Example:")
    print("-" * 80)
    
    import json
    json_output = json.dumps(results.to_dict(), indent=2)
    print(json_output[:500] + "..." if len(json_output) > 500 else json_output)

def test_checker():
    """Run tests on the code checker."""
    print("\n" + "=" * 80)
    print("Running Tests...")
    print("-" * 80)
    
    test_cases = [
        # Test 1: Unused import
        ('''
import os
import sys
x = 1
print(x)
''', [IssueType.UNUSED_IMPORT]),  # sys is unused
        
        # Test 2: Unused variable
        ('''
def test():
    x = 1
    y = 2
    print(x)
    return x
''', [IssueType.UNUSED_VARIABLE]),  # y is unused
        
        # Test 3: Long function
        ('\n'.join(['def long_func():'] + [f'    x{i} = {i}' for i in range(60)] + ['    return 0']),
         [IssueType.LONG_FUNCTION]),
        
        # Test 4: Deep nesting
        ('''
def nested():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        print("deep")
''', [IssueType.DEEP_NESTING]),
        
        # Test 5: Clean code (no issues)
        ('''
import os
def test():
    x = os.getcwd()
    return x
print(test())
''', []),
    ]
    
    for i, (code, expected_issues) in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        try:
            results = check_code(code)
            found_types = {issue.type for issue in results.issues}
            
            if set(expected_issues) == found_types:
                print(f"  ✓ PASS")
            else:
                print(f"  ✗ FAIL")
                print(f"    Expected: {[t.value for t in expected_issues]}")
                print(f"    Found: {[t.value for t in found_types]}")
                
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

if __name__ == "__main__":
    example_usage()
    test_checker()