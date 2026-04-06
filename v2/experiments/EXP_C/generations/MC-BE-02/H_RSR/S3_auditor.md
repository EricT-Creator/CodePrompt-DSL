## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — Python file using `from fastapi import FastAPI, HTTPException, Depends, Request, status`; app created with `FastAPI(...)`.
- C2 [!D]NO_JWT_LIB [AUTH]MANUAL_JWT: PASS — No JWT library (PyJWT, python-jose, authlib) imported; JWT implemented manually with `base64url_encode/decode`, `hmac.new(SECRET_KEY, ..., hashlib.sha256)`, and JSON header.payload.signature assembly.
- C3 [D]STDLIB+FASTAPI: PASS — All imports are stdlib (`base64`, `hmac`, `hashlib`, `json`, `time`, `uuid`, `dataclasses`, `typing`) or FastAPI/Pydantic; no external packages.
- C4 [O]SINGLE_FILE: PASS — All code (JWT encoding/decoding, auth middleware, endpoints, models) contained in a single file.
- C5 [API]LOGIN_PROTECTED_REFRESH: PASS — Three core endpoints: `/login` (username/password → access+refresh tokens), `/protected` (requires `Depends(require_auth)` with access token), `/refresh` (requires `Depends(require_refresh_token)`, issues new token pair with rotation).
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with docstrings and comments only.

## Functionality Assessment (0-5)
Score: 5 — Complete manual JWT authentication system: HMAC-SHA256 signing with constant-time comparison (`hmac.compare_digest`), base64url encoding without padding, access tokens (1h) and refresh tokens (7d) with token type enforcement, Bearer header extraction, mock user database with SHA-256 password hashing, refresh token rotation, health check, and custom HTTP exception handler with WWW-Authenticate header. Security-conscious implementation with proper separation of concerns.

## Corrected Code
No correction needed.
