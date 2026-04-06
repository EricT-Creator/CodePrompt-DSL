You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
TS + React. CSS Modules only, no Tailwind. HTML5 native drag, no dnd libs. useReducer only, no state libs. Single file, export default. Hand-written WS mock, no socket.io.

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints when two users move the same task simultaneously.
