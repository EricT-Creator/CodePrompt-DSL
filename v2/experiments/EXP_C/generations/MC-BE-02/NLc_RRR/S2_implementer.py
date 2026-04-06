import hmac
import hashlib
import base64
import json
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# ---- Configuration ----

SECRET_KEY = "super-secret-key-for-hmac-signing-2026"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ---- User Store ----

users: dict[str, str] = {
    "admin": "password123",
    "user1": "pass456",
}

# ---- Revoked Refresh Tokens ----

revoked_refresh_tokens: set[str] = set()

# ---- Base64URL Helpers ----


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ---- JWT Functions ----


def create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    encoded_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = b64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    encoded_header, encoded_payload, encoded_signature = parts

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_encoded = b64url_encode(expected_signature)

    if not hmac.compare_digest(encoded_signature, expected_encoded):
        return None

    try:
        payload_bytes = b64url_decode(encoded_payload)
        payload = json.loads(payload_bytes)
    except (json.JSONDecodeError, Exception):
        return None

    if "exp" in payload and payload["exp"] < time.time():
        return None

    return payload


def create_access_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        "type": "access",
    }
    return create_jwt(payload)


def create_refresh_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_EXPIRE_DAYS * 86400),
        "type": "refresh",
    }
    return create_jwt(payload)


# ---- Request Models ----

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---- FastAPI App ----

app = FastAPI(title="JWT Authentication System")
security = HTTPBearer()


# ---- Dependency ----

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    payload = verify_jwt(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return username


# ---- Endpoints ----

@app.post("/login")
async def login(request: LoginRequest) -> dict[str, str]:
    stored_password = users.get(request.username)
    if stored_password is None or stored_password != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(request.username)
    refresh_token = create_refresh_token(request.username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.get("/protected")
async def protected(user: str = Depends(get_current_user)) -> dict[str, str]:
    return {"user": user, "message": "Access granted"}


@app.post("/refresh")
async def refresh(request: RefreshRequest) -> dict[str, str]:
    payload = verify_jwt(request.refresh_token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = payload.get("sub")
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid user")

    token_id = f"{payload.get('sub')}:{payload.get('iat')}"
    if token_id in revoked_refresh_tokens:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    revoked_refresh_tokens.add(token_id)

    new_access_token = create_access_token(username)
    new_refresh_token = create_refresh_token(username)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
