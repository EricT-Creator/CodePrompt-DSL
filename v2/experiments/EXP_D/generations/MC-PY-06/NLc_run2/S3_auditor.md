## Constraint Review
- C1 [L]Python [D]STDLIB_ONLY: PASS — stdlib only
- C2 [!URL]SOCKET_RAW_HTTP (no urllib/http.client): **FAIL** — `from urllib.parse import urlparse, urlencode` at line 7
- C3 [!FSTR]NO_FSTRING (use .format() or %): PASS — `.format()` used exclusively
- C4 [TYPE]FULL_ANNOTATIONS: PASS — all public methods annotated
- C5 [RES]RESPONSE_DATACLASS: PASS — Response dataclass
- C6 [OUT]SINGLE_CLASS: PASS — single file class

## Functionality Assessment (0-5)
Score: 4 — Socket-based HTTP with redirect handling, urllib.parse violation.

## Corrected Code
No correction needed.
