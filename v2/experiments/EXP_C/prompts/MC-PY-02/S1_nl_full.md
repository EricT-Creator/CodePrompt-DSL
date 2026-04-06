You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use networkx, graphlib, or any graph library. Implement topological sort from scratch.
3. The main output must be a class (not standalone functions).
4. Full type annotations on all public methods.
5. Raise a custom CycleError exception when a cycle is detected.
6. Deliver a single Python file.

Include:
1. DAG data structure
2. Topological sort algorithm
3. Cycle detection approach
4. Parallel grouping strategy
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a DAG task scheduler: accept task dependency graph, perform topological sort, detect cycles (raise CycleError), group independent tasks for parallel execution, and provide an execute method that runs tasks in order.
