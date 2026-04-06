You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Must use ast.NodeVisitor or ast.walk for code analysis. Do not use regular expressions for code pattern matching.
3. Wrap all check results in dataclass instances.
4. Full type annotations on all public methods.
5. Implement all four checks: unused imports, unused variables, function length > 50 lines, nesting depth > 4.
6. Deliver a single Python file with a CodeChecker class.

Include:
1. AST visitor class hierarchy
2. Scope tracking for unused detection
3. Nesting depth calculation approach
4. Dataclass result schema
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a Python code checker that accepts source code as a string and checks: unused imports, unused variables, functions longer than 50 lines, and nesting depth exceeding 4 levels. Return results as dataclass instances.
