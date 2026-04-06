[L]TS [F]React [Y]CSS_MODULES [!Y]NO_TW [!D]NO_DND_LIB [DRAG]HTML5 [STATE]useReducer [O]SFC [EXP]DEFAULT [WS]MOCK [!D]NO_SOCKETIO

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it
6. **Constraint Checklist**: At the end of your document, output a section titled `## Constraint Checklist` with a numbered list. For each constraint, write one line in the format `[KEY] requirement` — a short identifier tag followed by the specific implementation requirement the developer must follow. Keep it compact and machine-readable. This checklist will be the developer's primary reference.

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints when two users move the same task simultaneously.
