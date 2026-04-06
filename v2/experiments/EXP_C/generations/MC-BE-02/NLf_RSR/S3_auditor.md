## Constraint Review
- C1 (Python + FastAPI): PASS — `from fastapi import FastAPI, HTTPException, Depends, Header`; `app = FastAPI(title="JWT Authentication System")`.
- C2 (Manual JWT, no PyJWT): PASS — `JWTManager` class implements JWT from scratch using `hmac.new()`, `hashlib.sha256`, `base64.urlsafe_b64encode/decode`, `json.dumps/loads`; no PyJWT/python-jose imported.
- C3 (stdlib + fastapi only): PASS — Imports only from standard library (hmac, hashlib, base64, json, time, uuid, datetime, typing) and fastapi/pydantic.
- C4 (Single file): PASS — All code (JWT implementation, user store, endpoints) in a single file.
- C5 (login/protected/refresh endpoints): PASS — `@app.post("/login")`, `@app.get("/protected")`, `@app.post("/refresh")` all present and functional.
- C6 (Code only): PASS — File contains only code with no explanation text outside of code comments.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with: manual JWT creation/verification with HS256 HMAC signing, base64url encoding with proper padding handling, constant-time signature comparison (`hmac.compare_digest`), access tokens (15min TTL) and refresh tokens (7-day TTL), token type validation, expiration checking, simulated user store with SHA-256 password hashing, token revocation tracking via JTI, refresh token rotation (old token revoked on refresh), logout endpoint that revokes both access and refresh tokens, protected endpoint with Bearer token extraction, and admin endpoints for user listing and revoked token inspection. Well-structured with clean separation of concerns.

## Corrected Code
No correction needed.
