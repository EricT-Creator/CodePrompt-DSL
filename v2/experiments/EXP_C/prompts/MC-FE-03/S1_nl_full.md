You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use TypeScript with React framework.
2. Use native Canvas 2D context API only. Do not use fabric.js, konva, p5.js, or any canvas/drawing library.
3. Use useReducer for ALL state management. Do not use useState at all.
4. No external npm packages beyond React and TypeScript.
5. Deliver a single .tsx file with export default.
6. Output code only, no explanation text.

Include:
1. Component architecture
2. Canvas drawing approach (event flow)
3. State model with useReducer (actions, state shape)
4. Undo/redo stack design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a canvas drawing whiteboard supporting pen tool, eraser, color picker, undo/redo, and clear canvas. Drawing should use mouse events (mousedown, mousemove, mouseup) to capture paths.
