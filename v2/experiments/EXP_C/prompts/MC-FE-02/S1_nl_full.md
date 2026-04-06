You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use TypeScript with React framework.
2. Implement virtual scrolling manually. Do not use react-window, react-virtualized, @tanstack/virtual, or any windowing library.
3. Use CSS Modules for all styling. Do not use Tailwind CSS or inline styles.
4. Do not use any external npm packages beyond React and TypeScript.
5. Deliver a single .tsx file with export default.
6. Generate mock data inline in the file. Do not import from external data files.

Include:
1. Component architecture
2. Virtual scrolling algorithm (how visible range is calculated)
3. Data model (TypeScript interfaces)
4. Sort and filter approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a virtual scroll data grid that renders 10,000 rows efficiently. Support fixed header, sortable columns (at least 2), and a search/filter input. Scrolling must be smooth with no visible flicker.
