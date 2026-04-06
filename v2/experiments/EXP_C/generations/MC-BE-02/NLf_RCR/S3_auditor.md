## Constraint Review
- C1 (Python + FastAPI): PASS — File uses `from fastapi import FastAPI, HTTPException, Depends` and defines `app = FastAPI()`.
- C2 (Manual JWT, no PyJWT): PASS — JWT creation and verification are implemented manually via `create_jwt()` and `verify_jwt()` using `hmac.new()`, `hashlib.sha256`, `base64.urlsafe_b64encode/decode`, and `json.dumps/loads`. No PyJWT or python-jose imported.
- C3 (stdlib + fastapi only): PASS — Imports are `base64`, `hashlib`, `hmac`, `json`, `time`, `uuid`, `typing` (all stdlib) plus `fastapi` and `pydantic`. `fastapi.security.HTTPBearer` is part of FastAPI.
- C4 (Single file): PASS — Everything is contained in a single Python file.
- C5 (login/protected/refresh endpoints): PASS — `POST /login`, `GET /protected`, and `POST /refresh` endpoints are all defined.
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth implementation with manual HS256 signing/verification, access + refresh token flow, token expiry checking, refresh token rotation with revocation set, constant-time password comparison via `hmac.compare_digest`, and proper HTTP Bearer auth dependency injection. Well-structured with clear separation of concerns.

## Corrected Code
No correction needed.
