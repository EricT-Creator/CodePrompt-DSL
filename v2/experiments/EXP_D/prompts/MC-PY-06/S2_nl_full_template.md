You are a developer. Implement the technical design below as a single Python file (.py). Follow ALL engineering constraints below strictly. Output code only, no explanation.

Engineering Constraints:
1. Use Python with standard library only.
2. Do NOT import or use urllib, http.client, or any HTTP library. Implement HTTP/1.1 request/response using the socket module directly (socket.create_connection, send raw bytes, recv response).
3. Do NOT use f-strings (f"...") anywhere in the code. Use str.format() or %-formatting exclusively for all string formatting.
4. All public methods must have complete type annotations (parameters and return types).
5. Define a Response dataclass with fields: status_code (int), headers (dict), body (str), elapsed_ms (float).
6. Implement as a single class in a single .py file.

Technical Design:
---
{S1_OUTPUT}
---
