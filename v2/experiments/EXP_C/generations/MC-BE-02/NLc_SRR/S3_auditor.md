## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import Depends, FastAPI, HTTPException, status` with Python standard library modules.
- C2 (Manual JWT, no PyJWT): PASS — JWT is manually implemented via `JWTManager` class using `hmac.new(..., hashlib.sha256)`, `base64.urlsafe_b64encode/decode`, and `json.dumps/loads`. No PyJWT or jose library imported.
- C3 (stdlib + fastapi only): PASS — Imports limited to stdlib (`base64`, `hashlib`, `hmac`, `json`, `uuid`, `dataclasses`, `datetime`, `typing`) plus `fastapi` and `pydantic` (bundled with fastapi). `uvicorn` imported only in `__main__`.
- C4 (Single file): PASS — All code (JWT implementation, user store, refresh token manager, endpoints) in one file.
- C5 (login/protected/refresh endpoints): PASS — `POST /auth/login`, `GET /auth/protected` (with Bearer auth dependency), and `POST /auth/refresh` are all implemented.
- C6 (Code only): PASS — File contains only executable code.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with manual HS256 signing, constant-time signature comparison (`hmac.compare_digest`), expiration checking, refresh token rotation with one-time-use enforcement, hashed refresh token storage, mock user database, and proper HTTP error responses with WWW-Authenticate headers.

## Corrected Code
No correction needed.
