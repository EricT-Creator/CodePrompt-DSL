[L]Python [D]STDLIB_ONLY [!URL]SOCKET_RAW_HTTP [!FSTR]NO_FSTRING [TYPE]FULL_ANNOTATIONS [RES]RESPONSE_DATACLASS [OUT]SINGLE_CLASS

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

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
