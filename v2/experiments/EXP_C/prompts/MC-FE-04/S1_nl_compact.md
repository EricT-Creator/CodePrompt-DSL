You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
TS + React. Hand-written validation, no formik/zod. Plain CSS, no Tailwind. No external deps. Single file, export default. Code only.

Include:
1. Step state machine design
2. Validation rules per step
3. Data model (TypeScript interfaces)
4. Navigation flow (forward with validation, backward preserving data)
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a 3-step form wizard: Step 1 (Personal Info: name, email, phone), Step 2 (Address: street, city, state, zip), Step 3 (Confirmation: display all entered data). Each step validates its fields before allowing forward navigation. Support back navigation that preserves entered data. Final submit collects all data.
