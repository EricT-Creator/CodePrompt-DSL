You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python 3.10+, stdlib only. No networkx/graphlib. Output as class. Full type annotations. CycleError on cycles. Single file.

Include:
1. DAG data structure
2. Topological sort algorithm
3. Cycle detection approach
4. Parallel grouping strategy
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a DAG task scheduler: accept task dependency graph, perform topological sort, detect cycles (raise CycleError), group independent tasks for parallel execution, and provide an execute method that runs tasks in order.
