import hmac
import hashlib
import base64
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 30 * 60  # 30 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days

USERS_DB = {
    "admin": "password123",
    "user": "mypassword",
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload: dict, expire_seconds: int) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + expire_seconds}

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> Optional[dict]:
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
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = verify_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


@app.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    if request.username not in USERS_DB or USERS_DB[request.username] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_jwt(
        {"sub": request.username, "type": "access"},
        ACCESS_TOKEN_EXPIRE,
    )
    refresh_token = create_jwt(
        {"sub": request.username, "type": "refresh"},
        REFRESH_TOKEN_EXPIRE,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.get("/protected")
def protected_route(user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello, {user['sub']}! You have access to this protected resource.",
        "user": user["sub"],
        "token_issued_at": user.get("iat"),
        "token_expires_at": user.get("exp"),
    }


@app.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest):
    payload = verify_jwt(request.refresh_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")

    username = payload["sub"]
    access_token = create_jwt(
        {"sub": username, "type": "access"},
        ACCESS_TOKEN_EXPIRE,
    )
    refresh_token = create_jwt(
        {"sub": username, "type": "refresh"},
        REFRESH_TOKEN_EXPIRE,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
