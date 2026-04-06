[L]PY310 [D]STDLIB_ONLY [!D]NO_IMPORTLIB [PLUGIN]EXEC [!D]NO_ABC [IFACE]PROTOCOL [TYPE]FULL_HINTS [ERR]ISOLATE [O]CLASS [FILE]SINGLE

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Pipeline class architecture
2. Plugin loading mechanism (exec flow)
3. Protocol interface definition
4. Conditional branch design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a plugin-based ETL data pipeline. Plugins implement a unified transform interface (Protocol). The pipeline loads plugins at runtime via exec(), runs them in sequence, supports conditional branches (some plugins only run when condition is met), and isolates errors so one plugin failure doesn't crash the pipeline.
