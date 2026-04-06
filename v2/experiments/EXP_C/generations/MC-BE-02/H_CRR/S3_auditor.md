## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — Written in Python using FastAPI framework (`from fastapi import FastAPI, HTTPException, Depends, Header`).
- C2 [!D]NO_JWT_LIB [AUTH]MANUAL_JWT: PASS — No external JWT library (`pyjwt`, `python-jose`, etc.) imported. JWT is manually implemented using `base64.urlsafe_b64encode`/`b64decode`, `hmac.new()` with SHA-256, and manual header/payload/signature construction in `create_token()`/`verify_token()`.
- C3 [D]STDLIB+FASTAPI: PASS — Imports are stdlib (`base64`, `hashlib`, `hmac`, `json`, `time`, `uuid`, `dataclasses`, `typing`) plus FastAPI ecosystem (`fastapi`, `pydantic`).
- C4 [O]SINGLE_FILE: PASS — All code (JWT implementation, models, endpoints, user store) resides in a single file.
- C5 [API]LOGIN_PROTECTED_REFRESH: PASS — Three key endpoints implemented: `POST /login` (returns access + refresh tokens), `GET /protected` (requires Bearer token via `get_current_user` dependency), `POST /refresh` (accepts refresh token, returns new access token).
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no extraneous narrative.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth middleware with: manual JWT creation/verification (HS256), proper base64url encoding with padding, signature verification via `hmac.compare_digest` (timing-safe), token expiration checks, separate access (15min) and refresh (7 day) token TTLs, in-memory user store, FastAPI dependency injection for auth, and proper HTTP 401 responses for invalid/missing tokens.

## Corrected Code
No correction needed.
