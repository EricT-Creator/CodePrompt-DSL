[L]PY310 [D]STDLIB_ONLY [MUST]AST_VISITOR [!D]NO_REGEX [O]DATACLASS [TYPE]FULL_HINTS [CHECK]IMPORT+VAR+LEN+NEST [O]CLASS [FILE]SINGLE

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. AST visitor class hierarchy
2. Scope tracking for unused detection
3. Nesting depth calculation approach
4. Dataclass result schema
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a Python code checker that accepts source code as a string and checks: unused imports, unused variables, functions longer than 50 lines, and nesting depth exceeding 4 levels. Return results as dataclass instances.
