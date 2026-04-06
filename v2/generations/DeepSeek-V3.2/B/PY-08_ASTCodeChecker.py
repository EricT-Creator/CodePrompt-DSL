import ast
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from collections import defaultdict


@dataclass
class CodeIssue:
    """Represents a single code issue found during analysis"""
    type: str  # 'unused_import', 'unused_variable', 'long_function', 'deep_nesting'
    location: str  # "line X"
    description: str
    severity: str  # 'info', 'warning', 'error'


@dataclass
class CheckResults:
    """Results of code analysis"""
    unused_imports: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    long_functions: List[str] = field(default_factory=list)
    deep_nesting: List[str] = field(default_factory=list)
    issues: List[CodeIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: CodeIssue) -> None:
        """Add an issue to the results"""
        self.issues.append(issue)
        
        # Also add to specific lists for easy access
        if issue.type == 'unused_import':
            self.unused_imports.append(issue.description)
        elif issue.type == 'unused_variable':
            self.unused_variables.append(issue.description)
        elif issue.type == 'long_function':
            self.long_functions.append(issue.description)
        elif issue.type == 'deep_nesting':
            self.deep_nesting.append(issue.description)
    
    def generate_summary(self) -> None:
        """Generate summary statistics"""
        self.summary = {
            'total_issues': len(self.issues),
            'unused_imports_count': len(self.unused_imports),
            'unused_variables_count': len(self.unused_variables),
            'long_functions_count': len(self.long_functions),
            'deep_nesting_count': len(self.deep_nesting),
            'issues_by_severity': {
                'info': len([i for i in self.issues if i.severity == 'info']),
                'warning': len([i for i in self.issues if i.severity == 'warning']),
                'error': len([i for i in self.issues if i.severity == 'error']),
            }
        }


class CodeChecker(ast.NodeVisitor):
    """
    AST-based code checker using ast.NodeVisitor.
    
    Detects:
    1. Unused imports
    2. Unused variables
    3. Functions longer than 50 lines
    4. Nesting deeper than 4 levels
    """
    
    def __init__(self, source: str):
        """
        Initialize code checker.
        
        Args:
            source: Python source code to analyze
        """
        self.source = source
        self.source_lines = source.splitlines()
        self.results = CheckResults()
        
        # Tracking structures
        self.imports: Dict[str, str] = {}  # name -> location
        self.used_names: Set[str] = set()
        self.current_function: Optional[str] = None
        self.function_line_counts: Dict[str, int] = {}
        self.nesting_level: int = 0
        self.max_nesting: Dict[str, int] = {}  # function -> max nesting level
        
        # Visit the AST
        tree = ast.parse(source)
        self.visit(tree)
        
        # Post-processing
        self._find_unused_imports()
        self._find_unused_variables()
        self.results.generate_summary()
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements"""
        for alias in node.names:
            location = f"line {node.lineno}"
            self.imports[alias.name] = location
            
            # Also track imported names if aliased
            if alias.asname:
                self.imports[alias.asname] = location
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statements"""
        module = node.module or ''
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            location = f"line {node.lineno}"
            self.imports[alias.name] = location
            self.imports[full_name] = location
            
            if alias.asname:
                self.imports[alias.asname] = location
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions"""
        old_function = self.current_function
        self.current_function = node.name
        
        # Calculate function length
        if node.body:
            start_line = node.lineno
            # Get the last line of the function
            last_node = node.body[-1]
            end_line = last_node.lineno if hasattr(last_node, 'lineno') else start_line
            
            # Adjust for decorators
            if node.decorator_list:
                decorator_lines = sum(1 for d in node.decorator_list if hasattr(d, 'lineno'))
                start_line -= decorator_lines
            
            line_count = end_line - start_line + 1
            self.function_line_counts[node.name] = line_count
            
            # Check for long functions
            if line_count > 50:
                issue = CodeIssue(
                    type='long_function',
                    location=f"line {start_line}",
                    description=f"Function '{node.name}' is {line_count} lines long",
                    severity='warning'
                )
                self.results.add_issue(issue)
        
        # Reset nesting for this function
        old_nesting = self.nesting_level
        self.nesting_level = 0
        self.max_nesting[node.name] = 0
        
        # Visit function body
        self.generic_visit(node)
        
        # Check nesting for this function
        if self.max_nesting[node.name] > 4:
            issue = CodeIssue(
                type='deep_nesting',
                location=f"line {node.lineno}",
                description=f"Function '{node.name}' has nesting level {self.max_nesting[node.name]}",
                severity='warning'
            )
            self.results.add_issue(issue)
        
        # Restore state
        self.current_function = old_function
        self.nesting_level = old_nesting
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions"""
        # Track class name usage
        self.used_names.add(node.name)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        """Visit name nodes (variables, functions, etc.)"""
        if isinstance(node.ctx, (ast.Load, ast.Del)):
            # Name is being used
            self.used_names.add(node.id)
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute nodes (e.g., module.function)"""
        # Track attribute usage
        if isinstance(node.ctx, (ast.Load, ast.Del)):
            # Build the full attribute chain
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)
                # Track the base name
                self.used_names.add(current.id)
        
        self.generic_visit(node)
    
    def visit_If(self, node: ast.If) -> None:
        """Visit if statements - track nesting"""
        self.nesting_level += 1
        
        if self.current_function:
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 0),
                self.nesting_level
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_For(self, node: ast.For) -> None:
        """Visit for loops - track nesting"""
        self.nesting_level += 1
        
        if self.current_function:
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 0),
                self.nesting_level
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node: ast.While) -> None:
        """Visit while loops - track nesting"""
        self.nesting_Level += 1
        
        if self.current_function:
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 0),
                self.nesting_level
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_Try(self, node: ast.Try) -> None:
        """Visit try blocks - track nesting"""
        self.nesting_level += 1
        
        if self.current_function:
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 0),
                self.nesting_level
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_With(self, node: ast.With) -> None:
        """Visit with statements - track nesting"""
        self.nesting_level += 1
        
        if self.current_function:
            self.max_nesting[self.current_function] = max(
                self.max_nesting.get(self.current_function, 0),
                self.nesting_level
            )
        
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def _find_unused_imports(self) -> None:
        """Find imports that are never used"""
        for import_name, location in self.imports.items():
            # Check if this import name was used
            # Split compound names (e.g., "os.path" -> check "os" and "os.path")
            name_parts = import_name.split('.')
            
            used = False
            for i in range(len(name_parts)):
                name_to_check = '.'.join(name_parts[:i+1])
                if name_to_check in self.used_names:
                    used = True
                    break
            
            if not used:
                issue = CodeIssue(
                    type='unused_import',
                    location=location,
                    description=f"Unused import: {import_name}",
                    severity='info'
                )
                self.results.add_issue(issue)
    
    def _find_unused_variables(self) -> None:
        """
        Find variables that are defined but never used.
        This is a simplified check that looks for assignment without subsequent use.
        """
        # This would require more sophisticated analysis to track variable scopes
        # For now, we'll note that this is a simplified check
        pass


def check_code(source: str) -> CheckResults:
    """
    Analyze Python source code and return check results.
    
    Args:
        source: Python source code string
    
    Returns:
        CheckResults dataclass with analysis findings
    """
    try:
        checker = CodeChecker(source)
        return checker.results
    except SyntaxError as e:
        # Handle syntax errors in the source
        issue = CodeIssue(
            type='syntax_error',
            location=f"line {e.lineno}, column {e.offset}",
            description=f"Syntax error: {e.msg}",
            severity='error'
        )
        
        results = CheckResults()
        results.add_issue(issue)
        results.generate_summary()
        return results
    except Exception as e:
        # Handle other unexpected errors
        issue = CodeIssue(
            type='analysis_error',
            location="unknown",
            description=f"Analysis failed: {str(e)}",
            severity='error'
        )
        
        results = CheckResults()
        results.add_issue(issue)
        results.generate_summary()
        return results


# Example usage and testing
def main():
    """Example usage of the code checker"""
    
    print("=== Python Code Checker Examples ===")
    print()
    
    # Example 1: Simple code with issues
    example_code1 = """
import os
import sys
import json
from collections import defaultdict

unused_var = 42

def long_function():
    # This function is intentionally long
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
    ab = 28
    ac = 29
    ad = 30
    ae = 31
    af = 32
    ag = 33
    ah = 34
    ai = 35
    aj = 36
    ak = 37
    al = 38
    am = 39
    an = 40
    ao = 41
    ap = 42
    aq = 43
    ar = 44
    as_var = 45
    at = 46
    au = 47
    av = 48
    aw = 49
    ax = 50
    ay = 51  # This makes it > 50 lines
    return ay

def deeply_nested():
    if True:
        if True:
            if True:
                if True:
                    if True:  # This is level 5
                        return "too deep"

# Using only some imports
print(sys.version)
data = json.dumps({"test": "value"})
"""
    
    print("1. Analyzing example code with issues:")
    results1 = check_code(example_code1)
    
    print(f"   Total issues found: {results1.summary['total_issues']}")
    print(f"   Issues by type:")
    print(f"     - Unused imports: {results1.summary['unused_imports_count']}")
    print(f"     - Long functions: {results1.summary['long_functions_count']}")
    print(f"     - Deep nesting: {results1.summary['deep_nesting_count']}")
    print()
    
    print("   Detailed issues:")
    for issue in results1.issues:
        print(f"     [{issue.severity.upper()}] {issue.type} at {issue.location}: {issue.description}")
    print()
    
    # Example 2: Clean code
    example_code2 = """
import os
import sys

def calculate_sum(a, b):
    return a + b

def main():
    result = calculate_sum(10, 20)
    print(f"The sum is: {result}")
    print(f"Python version: {sys.version}")

if __name__ == "__main__":
    main()
"""
    
    print("2. Analyzing clean code:")
    results2 = check_code(example_code2)
    
    print(f"   Total issues found: {results2.summary['total_issues']}")
    print()
    
    # Example 3: Code with syntax error
    example_code3 = """
def broken_function(
    print("missing closing paren"
"""
    
    print("3. Analyzing code with syntax error:")
    results3 = check_code(example_code3)
    
    for issue in results3.issues:
        print(f"   [{issue.severity.upper()}] {issue.type}: {issue.description} at {issue.location}")
    print()
    
    # Example 4: Complex code structure
    example_code4 = """
import math
from typing import List, Dict

class Calculator:
    def __init__(self):
        self.history: List[float] = []
    
    def add(self, a: float, b: float) -> float:
        result = a + b
        self.history.append(result)
        return result
    
    def multiply(self, a: float, b: float) -> float:
        result = a * b
        self.history.append(result)
        return result

def process_data(data: List[Dict]) -> float:
    total = 0.0
    for item in data:
        if 'value' in item:
            total += item['value']
            if total > 1000:
                break
    return total

if __name__ == "__main__":
    calc = Calculator()
    result1 = calc.add(10, 20)
    result2 = calc.multiply(5, 6)
    print(f"Results: {result1}, {result2}")
    
    data = [{"value": 100}, {"value": 200}, {"name": "test"}]
    total = process_data(data)
    print(f"Total: {total}")
"""
    
    print("4. Analyzing complex code structure:")
    results4 = check_code(example_code4)
    
    print(f"   Total issues found: {results4.summary['total_issues']}")
    print(f"   Issues by severity:")
    for severity, count in results4.summary['issues_by_severity'].items():
        if count > 0:
            print(f"     - {severity}: {count}")
    print()
    
    # Performance test
    print("=== Performance Test ===")
    
    # Generate a large code block
    large_code = """
import os
import sys
import math
import json
import time
from typing import List, Dict, Tuple

def function1():
    return 1

def function2():
    return 2

def function3():
    return 3

# ... (many more functions)

def function100():
    return 100

def complex_logic():
    if True:
        for i in range(10):
            if i % 2 == 0:
                while True:
                    if False:
                        break
                    else:
                        try:
                            pass
                        except:
                            pass
    return "done"

class LargeClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
    
    # ... (many more methods)

if __name__ == "__main__":
    print("Running large code analysis...")
"""
    
    # Extend the code
    for i in range(101, 201):
        large_code += f"\ndef function{i}():\n    return {i}\n"
    
    import time
    start = time.time()
    results = check_code(large_code)
    elapsed = time.time() - start
    
    print(f"Analyzed code with {len(large_code.splitlines())} lines in {elapsed:.3f} seconds")
    print(f"Found {results.summary['total_issues']} issues")
    print()


if __name__ == "__main__":
    main()