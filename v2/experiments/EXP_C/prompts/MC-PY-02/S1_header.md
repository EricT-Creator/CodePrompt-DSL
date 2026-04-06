[L]PY310 [D]STDLIB_ONLY [!D]NO_GRAPH_LIB [O]CLASS [TYPE]FULL_HINTS [ERR]CYCLE_EXC [FILE]SINGLE

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. DAG data structure
2. Topological sort algorithm
3. Cycle detection approach
4. Parallel grouping strategy
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a DAG task scheduler: accept task dependency graph, perform topological sort, detect cycles (raise CycleError), group independent tasks for parallel execution, and provide an execute method that runs tasks in order.
