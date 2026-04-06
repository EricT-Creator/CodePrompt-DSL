[L]TS [F]React [!D]NO_CANVAS_LIB [DRAW]CTX2D [STATE]useReducer_ONLY [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Component architecture
2. Canvas drawing approach (event flow)
3. State model with useReducer (actions, state shape)
4. Undo/redo stack design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a canvas drawing whiteboard supporting pen tool, eraser, color picker, undo/redo, and clear canvas. Drawing should use mouse events (mousedown, mousemove, mouseup) to capture paths.
