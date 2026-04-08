# Technical Design: HTTP Request Builder (Socket-based)

## Overview
Python class that sends HTTP/1.1 requests using raw sockets (no urllib/http.client), with str.format() formatting (no f-strings).

## HTTP/1.1 Protocol Implementation

### Request Building
1. Parse URL: extract host, port (default 80 for http, 443 for https), path, query
2. Build request line: `"{method} {path} HTTP/1.1\r\n".format(method=method, path=full_path)`
3. Build headers: Host, Content-Length (for POST/PUT), Content-Type, custom headers
4. Build body: JSON serialization using json.dumps for json_body parameter
5. Concatenate: request_line + headers + "\r\n" + body

### Socket Communication
1. `sock = socket.create_connection((host, port), timeout=timeout)`
2. `sock.sendall(request_bytes)`
3. `response_data = b""` then loop `sock.recv(4096)` until empty
4. Close socket

### Response Parsing
1. Split on `\r\n\r\n` to separate headers from body
2. Parse status line: `HTTP/1.1 {code} {reason}`
3. Parse headers into dict
4. Handle Content-Length vs chunked transfer
5. Decode body as UTF-8

### Redirect Handling
- If status 301/302, read Location header
- Repeat request to new URL (up to 5 redirects)
- Track redirect count, raise error if exceeded

## String Formatting Rule
ALL string construction uses `.format()` or `%` formatting:
- `"GET {path} HTTP/1.1\r\n".format(path=path)`
- `"Host: %s\r\n" % host`
- NEVER use `f"..."` anywhere

## Data Classes

```
@dataclass
class Response:
    status_code: int
    headers: dict[str, str]
    body: str
    elapsed_ms: float
```

## Public API

- `get(self, url: str, headers: dict | None = None, params: dict | None = None, timeout: float = 30.0) -> Response`
- `post(self, url: str, headers: dict | None = None, json_body: dict | None = None, timeout: float = 30.0) -> Response`
- `put(self, url: str, headers: dict | None = None, json_body: dict | None = None, timeout: float = 30.0) -> Response`
- `delete(self, url: str, headers: dict | None = None, timeout: float = 30.0) -> Response`

## Constraint Acknowledgment
- C1: Python stdlib only
- C2: NO urllib/http.client — raw socket only
- C3: NO f-strings — .format() and % formatting only
- C4: Full type annotations
- C5: Response dataclass
- C6: Single file class
