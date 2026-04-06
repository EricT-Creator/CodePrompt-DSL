You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
TS + React. Manual virtual scroll, no react-window. CSS Modules, no Tailwind/inline. No external deps. Single file, export default. Inline mock data.

Include:
1. Component architecture
2. Virtual scrolling algorithm (how visible range is calculated)
3. Data model (TypeScript interfaces)
4. Sort and filter approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a virtual scroll data grid that renders 10,000 rows efficiently. Support fixed header, sortable columns (at least 2), and a search/filter input. Scrolling must be smooth with no visible flicker.
