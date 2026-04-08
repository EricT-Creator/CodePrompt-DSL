You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use Python with standard library only.
2. Do NOT import or use urllib, http.client, or any HTTP library. Implement HTTP/1.1 request/response using the socket module directly (socket.create_connection, send raw bytes, recv response).
3. Do NOT use f-strings (f"...") anywhere in the code. Use str.format() or %-formatting exclusively for all string formatting.
4. All public methods must have complete type annotations (parameters and return types).
5. Define a Response dataclass with fields: status_code (int), headers (dict), body (str), elapsed_ms (float).
6. Implement as a single class in a single .py file.

Include:
1. Socket-level HTTP/1.1 implementation (NOT urllib/http.client)
2. Request building with .format()/% formatting (NOT f-strings)
3. Response parsing (status line, headers, body)
4. Redirect handling (301/302)
5. Response dataclass design
6. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Write a Python class `HTTPClient` that builds and sends HTTP/1.1 requests. Support methods: get(url, headers=None, params=None, timeout=30), post(url, headers=None, json_body=None, timeout=30), put(...), delete(...). Parse response into a Response object with status_code, headers (dict), body (str), elapsed_ms (float). Handle redirects (301/302) up to 5 times. Handle connection timeout.
