You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with standard library only.
2. Do NOT import or use urllib, http.client, or any HTTP library. Implement HTTP/1.1 request/response using the socket module directly (socket.create_connection, send raw bytes, recv response).
3. Do NOT use f-strings (f"...") anywhere in the code. Use str.format() or %-formatting exclusively for all string formatting.
4. All public methods must have complete type annotations (parameters and return types).
5. Define a Response dataclass with fields: status_code (int), headers (dict), body (str), elapsed_ms (float).
6. Implement as a single class in a single .py file.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [D]STDLIB_ONLY: PASS/FAIL — evidence
- C2 [!URL]SOCKET_RAW_HTTP (no urllib/http.client): PASS/FAIL — evidence
- C3 [!FSTR]NO_FSTRING (use .format() or %): PASS/FAIL — evidence
- C4 [TYPE]FULL_ANNOTATIONS: PASS/FAIL — evidence
- C5 [RES]RESPONSE_DATACLASS: PASS/FAIL — evidence
- C6 [OUT]SINGLE_CLASS: PASS/FAIL — evidence

## Functionality Assessment (0-5)
Score: X — brief justification

## Corrected Code
If ANY constraint is FAIL, output the COMPLETE corrected .py file below. If all PASS, output "No correction needed."

```py
{corrected code here if needed}
```

Code to review:
---
{S2_OUTPUT}
---
