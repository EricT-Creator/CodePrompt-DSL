You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python 3.10+, stdlib only. Regex parsing, no jinja2/mako. No ast module. Full type annotations. TemplateSyntaxError on errors. Single file, class output.

Include:
1. Regex patterns for each template construct
2. Parsing strategy (recursive/stack-based)
3. Filter pipeline design
4. Error handling approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a template engine supporting: {{var}} variable substitution, {%% if cond %%}...{%% endif %%} conditionals, {%% for item in list %%}...{%% endfor %%} loops, {{var|filter}} filter pipes (at least upper, lower, capitalize), and nested if/for structures.
