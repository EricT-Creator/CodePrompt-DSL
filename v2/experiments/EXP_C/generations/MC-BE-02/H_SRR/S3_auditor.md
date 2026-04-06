## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — Python file using `from fastapi import Depends, FastAPI, HTTPException, status`
- C2 [!D]NO_JWT_LIB [AUTH]MANUAL_JWT: PASS — No JWT library imported; JWT manually implemented using `hmac.new()` + `hashlib.sha256` + `base64.urlsafe_b64encode/decode` + `json` for header/payload/signature
- C3 [D]STDLIB+FASTAPI: PASS — Only stdlib imports (`base64, hashlib, hmac, json, time, typing`) plus FastAPI/Pydantic
- C4 [O]SINGLE_FILE: PASS — All code in a single file
- C5 [API]LOGIN_PROTECTED_REFRESH: PASS — Three auth endpoints: `POST /api/v1/auth/login` (returns access + refresh tokens), `GET /api/v1/auth/protected` (requires Bearer token via `get_current_user` dependency), `POST /api/v1/auth/refresh` (token rotation with old token blacklisting)
- C6 [OUT]CODE_ONLY: PASS — Output is pure Python code with no prose

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with manual HMAC-SHA256 signing, base64url encoding, expiration checking, timing-safe signature comparison (`hmac.compare_digest`), token blacklist for revocation, token rotation on refresh, role-based claims, mock user store, and proper HTTP 401/403 error responses with `WWW-Authenticate` headers.

## Corrected Code
No correction needed.
