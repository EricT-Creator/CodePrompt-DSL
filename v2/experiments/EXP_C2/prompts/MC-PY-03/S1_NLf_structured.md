You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use jinja2, mako, or any template library. Parse templates using regular expressions.
3. Do not use the ast module for expression evaluation.
4. Full type annotations on all public methods.
5. Raise a custom TemplateSyntaxError for malformed templates.
6. Deliver a single Python file with a TemplateEngine class.

Include:
1. Regex patterns for each template construct
2. Parsing strategy (recursive/stack-based)
3. Filter pipeline design
4. Error handling approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it
6. **Constraint Checklist**: At the end of your document, output a section titled `## Constraint Checklist` with a numbered list. For each constraint, write one line in the format `[KEY] requirement` — a short identifier tag followed by the specific implementation requirement the developer must follow. Keep it compact and machine-readable. This checklist will be the developer's primary reference.

Do NOT write code. Output the design document only.

User Requirement:
Build a template engine supporting: {{var}} variable substitution, {% if cond %}...{% endif %} conditionals, {% for item in list %}...{% endfor %} loops, {{var|filter}} filter pipes (at least upper, lower, capitalize), and nested if/for structures.
