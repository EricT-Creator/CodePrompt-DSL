You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use TypeScript with React framework.
2. Use CSS Modules for all styling. Do not use Tailwind CSS or any utility-first CSS framework.
3. Implement drag-and-drop using the native HTML5 Drag and Drop API only. Do not use react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library.
4. Use useReducer for all state management. Do not use Redux, Zustand, Jotai, or other state management libraries.
5. Deliver a single .tsx file with export default as the main component.
6. Simulate real-time sync with a hand-written mock using setTimeout/setInterval. Do not use socket.io or any WebSocket library.

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints when two users move the same task simultaneously.
