[L]TS [F]React [!D]NO_FORM_LIB [VALID]HANDWRITE [Y]PLAIN_CSS [!Y]NO_TW [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Step state machine design
2. Validation rules per step
3. Data model (TypeScript interfaces)
4. Navigation flow (forward with validation, backward preserving data)
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a 3-step form wizard: Step 1 (Personal Info: name, email, phone), Step 2 (Address: street, city, state, zip), Step 3 (Confirmation: display all entered data). Each step validates its fields before allowing forward navigation. Support back navigation that preserves entered data. Final submit collects all data.
