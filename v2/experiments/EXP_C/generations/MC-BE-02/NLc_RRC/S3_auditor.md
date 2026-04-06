# MC-BE-02 Code Review Report (NLc_RRC)

## Constraint Review

- C1 (Python + FastAPI): PASS — Uses Python with FastAPI framework (line 1987)
- C2 (Manual JWT, no PyJWT): PASS — Implements JWT using `hmac` and `base64` from stdlib (lines 1980-1985, 2050-2086), no PyJWT/python-jose
- C3 (stdlib + fastapi only): FAIL — Uses `pydantic` (line 1988) which is a third-party package, not in stdlib
- C4 (Single file): PASS — All code delivered in a single Python file
- C5 (login/protected/refresh endpoints): PASS — Provides POST /login (line 2138), GET /protected (line 2154), POST /refresh (line 2159)
- C6 (Code only): PASS — Output contains code only, no explanation text

## Functionality Assessment (0-5)
Score: 4 — The code correctly implements manual JWT signing/verification using HMAC-SHA256 with stdlib only, and provides all required endpoints. However, it violates C3 by using pydantic which is not in Python standard library.

## Corrected Code

```py
import hmac
import hashlib
import base64
import json
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Header


# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE = 15 * 60      # 15 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 3600  # 7 days

# ─── User Store ───────────────────────────────────────────────────────────────

users: dict[str, str] = {
    "admin": "password123",
    "user1": "pass456",
}

# ─── Revoked Refresh Tokens ──────────────────────────────────────────────────

revoked_refresh_tokens: set[str] = set()


# ─── Base64URL Helpers ────────────────────────────────────────────────────────

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ─── JWT Functions ────────────────────────────────────────────────────────────

def create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = base64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid signature")

    payload = json.loads(base64url_decode(encoded_payload))

    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token expired")

    return payload


def create_access_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_EXPIRE),
        "type": "access",
    }
    return create_jwt(payload)


def create_refresh_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_EXPIRE),
        "type": "refresh",
    }
    return create_jwt(payload)


# ─── FastAPI Dependency ───────────────────────────────────────────────────────

async def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    try:
        payload = verify_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return username


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/login")
async def login(request: dict) -> dict:
    username = request.get("username", "")
    password = request.get("password", "")
    
    stored_password = users.get(username)
    if stored_password is None or stored_password != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(username)
    refresh_token = create_refresh_token(username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.get("/protected")
async def protected(authorization: str = Header(...)) -> dict:
    user = await get_current_user(authorization)
    return {"user": user, "message": "Access granted"}


@app.post("/refresh")
async def refresh(request: dict) -> dict:
    refresh_token = request.get("refresh_token", "")
    
    try:
        payload = verify_jwt(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type: expected refresh token")

    if refresh_token in revoked_refresh_tokens:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    username = payload.get("sub")
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid user")

    revoked_refresh_tokens.add(refresh_token)
    access_token = create_access_token(username)

    return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
