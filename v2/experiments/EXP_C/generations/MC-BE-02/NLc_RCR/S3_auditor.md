## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException, Depends, Header` and defines `app = FastAPI()` with route decorators.
- C2 (Manual JWT, no PyJWT): PASS — JWT creation and verification implemented manually via `base64url_encode`/`base64url_decode`, `hmac.new()` with `hashlib.sha256`, and `json` serialization in `create_jwt()` (line 1596) and `verify_jwt()` (line 1609); no PyJWT import.
- C3 (stdlib + fastapi only): PASS — Imports only `json`, `base64`, `hmac`, `hashlib`, `time`, `typing` (all stdlib), plus `fastapi`, `pydantic` (bundled with fastapi), and `uvicorn`.
- C4 (Single file): PASS — All logic (JWT functions, auth dependency, endpoints) contained in one file.
- C5 (login/protected/refresh endpoints): PASS — `/login` (POST, line 1657), `/protected` (GET, line 1664), `/refresh` (POST, line 1668) all present and functional.
- C6 (Code only): PASS — File contains only executable Python code; no prose or markdown.

## Functionality Assessment (0-5)
Score: 5 — Implements a complete JWT auth system with: manual HS256 JWT creation/verification using hmac+base64, access tokens (15min TTL) and refresh tokens (7-day TTL), token type validation, refresh token rotation with one-time-use enforcement via `used_refresh_tokens` set, expiration checking, HTTPBearer security dependency, and proper error handling. The manual JWT implementation correctly follows the JWS Compact Serialization format.

## Corrected Code
No correction needed.
