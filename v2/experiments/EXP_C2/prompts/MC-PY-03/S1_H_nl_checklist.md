[L]PY310 [D]STDLIB_ONLY [!D]NO_TMPL_LIB [PARSE]REGEX [!D]NO_AST [TYPE]FULL_HINTS [ERR]SYNTAX_EXC [O]CLASS [FILE]SINGLE

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Regex patterns for each template construct
2. Parsing strategy (recursive/stack-based)
3. Filter pipeline design
4. Error handling approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it
6. **Constraint Checklist**: At the end of your document, output a section titled `## Constraint Checklist` with a numbered list. For each constraint, write one complete natural-language sentence describing what the developer must do or avoid. Use plain English, no abbreviations or tags. This checklist will be the developer's primary reference.

Do NOT write code. Output the design document only.

User Requirement:
Build a template engine supporting: {{var}} variable substitution, {% if cond %}...{% endif %} conditionals, {% for item in list %}...{% endfor %} loops, {{var|filter}} filter pipes (at least upper, lower, capitalize), and nested if/for structures.
