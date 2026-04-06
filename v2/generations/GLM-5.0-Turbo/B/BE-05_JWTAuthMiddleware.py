import hashlib
import hmac
import base64
import json
import time
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

SECRET_KEY = "super-secret-key-2026-change-in-production"
TOKEN_EXPIRY_SECONDS = 30 * 60  # 30 minutes

# In-memory user store
USERS = {
    "admin": "password123",
    "alice": "wonderland",
    "bob": "builder",
}

# In-memory token blacklist (for refresh invalidation)
REVOKED_TOKENS: set = set()


# ===== Manual JWT Implementation (HMAC + Base64url) =====

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    return f"{signing_input}.{signature_b64}"


def decode_jwt(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = base64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(base64url_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ===== Models =====

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    token: str


# ===== Middleware =====

@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/login", "/refresh", "/docs", "/openapi.json", "/"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid Authorization header"},
        )

    token = auth_header[7:]
    if token in REVOKED_TOKENS:
        return JSONResponse(
            status_code=401,
            content={"detail": "Token has been revoked"},
        )

    payload = decode_jwt(token)
    if payload is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    request.state.user = payload.get("sub")
    request.state.token_payload = payload
    return await call_next(request)


# ===== Routes =====

@app.post("/login")
async def login(body: LoginRequest):
    if body.username not in USERS or USERS[body.username] != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = time.time()
    payload = {
        "sub": body.username,
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
    }
    token = create_jwt(payload)
    return {
        "token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }


@app.get("/protected")
async def protected(request: Request):
    username = getattr(request.state, "user", "unknown")
    return {
        "message": f"Hello, {username}! You have accessed a protected resource.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/refresh")
async def refresh(body: RefreshRequest):
    payload = decode_jwt(body.token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Revoke old token
    REVOKED_TOKENS.add(body.token)

    # Issue new token
    now = time.time()
    new_payload = {
        "sub": payload["sub"],
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
    }
    new_token = create_jwt(new_payload)
    return {
        "token": new_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
