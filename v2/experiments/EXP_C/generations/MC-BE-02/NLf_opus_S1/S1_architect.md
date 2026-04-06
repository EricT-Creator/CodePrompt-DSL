# Technical Design Document — JWT Authentication System

## 1. Overview

This document describes the architecture for a FastAPI JWT authentication system. The system provides POST /login to issue a JWT, GET /protected to verify the JWT and return user data (401 on invalid token), and POST /refresh to refresh an expiring token. JWT signing uses HMAC-SHA256 implemented manually with the standard library's `hmac` and `base64` modules.

## 2. JWT Structure

### 2.1 Token Format

A JWT consists of three base64url-encoded parts separated by dots:

```
header.payload.signature
```

- **Header**: `{ "alg": "HS256", "typ": "JWT" }`
- **Payload**: `{ "sub": "<user_id>", "username": "<name>", "iat": <issued_at_timestamp>, "exp": <expiry_timestamp>, "type": "access" | "refresh" }`
- **Signature**: `HMAC-SHA256(base64url(header) + "." + base64url(payload), secret_key)`

### 2.2 Base64url Encoding

Standard base64 with the following substitutions to make it URL-safe:
- `+` → `-`
- `/` → `_`
- Strip trailing `=` padding

This is implemented manually using `base64.urlsafe_b64encode` with padding removal.

## 3. HMAC-SHA256 Signing Flow

### 3.1 Token Creation

1. Construct the header dict → serialize to JSON → base64url encode → `header_b64`.
2. Construct the payload dict (with `sub`, `username`, `iat`, `exp`, `type`) → serialize to JSON → base64url encode → `payload_b64`.
3. Create the signing input: `f"{header_b64}.{payload_b64}"`.
4. Compute HMAC-SHA256: `hmac.new(secret_key.encode(), signing_input.encode(), hashlib.sha256).digest()`.
5. Base64url encode the signature bytes → `signature_b64`.
6. Return `f"{header_b64}.{payload_b64}.{signature_b64}"`.

### 3.2 Token Verification

1. Split the token by `.` into `[header_b64, payload_b64, signature_b64]`.
2. Recompute the signature: `HMAC-SHA256(header_b64 + "." + payload_b64, secret_key)`.
3. Base64url encode the recomputed signature.
4. Compare with `signature_b64` using `hmac.compare_digest()` (constant-time comparison to prevent timing attacks).
5. If signatures match, decode the payload and check `exp` against the current timestamp.
6. If expired or signature mismatch, reject the token.

## 4. Token Refresh Logic

### 4.1 Two-Token Strategy

- **Access token**: Short-lived (e.g., 15 minutes). Used for authenticating requests to protected endpoints.
- **Refresh token**: Longer-lived (e.g., 7 days). Used only at the /refresh endpoint to obtain a new access token.

Both tokens use the same JWT structure but differ in the `type` field (`"access"` vs `"refresh"`) and `exp` duration.

### 4.2 Refresh Flow

1. Client sends POST `/refresh` with the refresh token in the request body.
2. Server verifies the refresh token (signature + expiry + type == "refresh").
3. If valid, issue a new access token (and optionally a new refresh token).
4. If invalid or expired, return 401.

### 4.3 Token Revocation

Since no external storage is used, a simple in-memory set of revoked token IDs (or `jti` claims) can be maintained. On refresh, the old refresh token's `jti` is added to the revoked set. This prevents replay of used refresh tokens.

## 5. Middleware / Dependency Design

### 5.1 FastAPI Dependency

A `get_current_user` dependency function is used on protected routes:

1. Extract the `Authorization` header.
2. Verify it starts with `"Bearer "`.
3. Extract the token string.
4. Call the token verification function.
5. If valid, return the decoded user payload.
6. If invalid, raise `HTTPException(status_code=401, detail="Invalid or expired token")`.

### 5.2 User Store

A simple in-memory dictionary simulates a user database:
```
users = { "user1": { "username": "user1", "password_hash": "<hashed>", "user_id": "u-001" }, ... }
```

Password verification uses `hmac.compare_digest` against a stored hash (hashed via `hashlib.sha256`).

### 5.3 Endpoint Structure

| Endpoint | Auth Required | Description |
|----------|--------------|-------------|
| POST /login | No | Accepts username/password, returns access + refresh tokens |
| GET /protected | Yes (access token) | Returns the authenticated user's data |
| POST /refresh | No (but requires valid refresh token in body) | Returns a new access token |

## 6. Error Handling

- **Invalid credentials** (login): 401 with `"Invalid username or password"`.
- **Missing Authorization header**: 401 with `"Authorization header missing"`.
- **Malformed token**: 401 with `"Invalid token format"`.
- **Signature mismatch**: 401 with `"Invalid token signature"`.
- **Expired token**: 401 with `"Token has expired"`.
- **Wrong token type** (e.g., access token sent to /refresh): 401 with `"Invalid token type"`.

## 7. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python with FastAPI | The entire system is built on FastAPI with Pydantic request/response models. |
| 2 | No PyJWT/python-jose; implement JWT with hmac and base64 | JWT creation and verification are implemented from scratch using `hmac.new()`, `hashlib.sha256`, and `base64.urlsafe_b64encode/decode`. No JWT library is imported. |
| 3 | Only Python stdlib, fastapi, and uvicorn | All cryptographic operations use `hmac`, `hashlib`, `base64`, `json`, and `time` from the standard library. No additional packages. |
| 4 | Single Python file | All endpoint definitions, JWT functions, user store, and middleware are in one `.py` file. |
| 5 | Minimum POST /login, GET /protected, POST /refresh | All three endpoints are included as core API surface. |
| 6 | Output code only, no explanation text | The final implementation will be pure code. This document is the design artifact. |
