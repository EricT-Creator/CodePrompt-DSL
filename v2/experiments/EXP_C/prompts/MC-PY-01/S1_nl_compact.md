You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python 3.10+, stdlib only. exec() for plugin loading, no importlib. Protocol for interfaces, no ABC. Full type annotations. Plugin errors isolated. Single file, class output.

Include:
1. Pipeline class architecture
2. Plugin loading mechanism (exec flow)
3. Protocol interface definition
4. Conditional branch design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a plugin-based ETL data pipeline. Plugins implement a unified transform interface (Protocol). The pipeline loads plugins at runtime via exec(), runs them in sequence, supports conditional branches (some plugins only run when condition is met), and isolates errors so one plugin failure doesn't crash the pipeline.
