import hmac
import hashlib
import base64
import json
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel


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

# ─── Request / Response Models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProtectedResponse(BaseModel):
    user: str
    message: str


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


@app.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    stored_password = users.get(req.username)
    if stored_password is None or stored_password != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(req.username)
    refresh_token = create_refresh_token(req.username)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected(user: str = Depends(get_current_user)) -> ProtectedResponse:
    return ProtectedResponse(user=user, message="Access granted")


@app.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest) -> RefreshResponse:
    try:
        payload = verify_jwt(req.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type: expected refresh token")

    if req.refresh_token in revoked_refresh_tokens:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    username = payload.get("sub")
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid user")

    revoked_refresh_tokens.add(req.refresh_token)
    access_token = create_access_token(username)

    return RefreshResponse(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
