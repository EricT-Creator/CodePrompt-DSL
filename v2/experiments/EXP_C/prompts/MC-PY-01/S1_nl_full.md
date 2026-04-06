You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use importlib for plugin loading. Load plugins by reading the file and using exec().
3. Do not use ABC (Abstract Base Class). Define interfaces using typing.Protocol.
4. Full type annotations on all public methods and class attributes.
5. Plugin errors must be isolated. One plugin failure must not crash the pipeline.
6. Deliver a single Python file with a Pipeline class as main output.

Include:
1. Pipeline class architecture
2. Plugin loading mechanism (exec flow)
3. Protocol interface definition
4. Conditional branch design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a plugin-based ETL data pipeline. Plugins implement a unified transform interface (Protocol). The pipeline loads plugins at runtime via exec(), runs them in sequence, supports conditional branches (some plugins only run when condition is met), and isolates errors so one plugin failure doesn't crash the pipeline.
