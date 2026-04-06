[L]TS [F]React [!D]NO_VIRT_LIB [SCROLL]MANUAL [Y]CSS_MODULES [!Y]NO_TW_INLINE [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [DT]INLINE_MOCK

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Component architecture
2. Virtual scrolling algorithm (how visible range is calculated)
3. Data model (TypeScript interfaces)
4. Sort and filter approach
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a virtual scroll data grid that renders 10,000 rows efficiently. Support fixed header, sortable columns (at least 2), and a search/filter input. Scrolling must be smooth with no visible flicker.
