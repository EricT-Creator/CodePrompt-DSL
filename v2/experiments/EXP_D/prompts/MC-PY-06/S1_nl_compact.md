You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python stdlib only. DO NOT use urllib or http.client — implement HTTP using raw socket. DO NOT use f-strings — use .format() or % formatting only. Full type annotations. Response as dataclass. Single file class.

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
