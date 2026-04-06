You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use TypeScript with React framework.
2. Implement all form validation by hand. Do not use react-hook-form, formik, zod, yup, or any form/validation library.
3. Use plain CSS (style tags or CSS files) for styling. Do not use Tailwind CSS.
4. No external npm packages beyond React and TypeScript.
5. Deliver a single .tsx file with export default.
6. Output code only, no explanation text.

Include:
1. Step state machine design
2. Validation rules per step
3. Data model (TypeScript interfaces)
4. Navigation flow (forward with validation, backward preserving data)
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a 3-step form wizard: Step 1 (Personal Info: name, email, phone), Step 2 (Address: street, city, state, zip), Step 3 (Confirmation: display all entered data). Each step validates its fields before allowing forward navigation. Support back navigation that preserves entered data. Final submit collects all data.
