import hashlib
import hmac
import base64
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="JWT Auth Middleware")

SECRET_KEY = "super-secret-key-for-hmac-signing-2024"
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 30 * 60  # 30 minutes

USERS_DB = {
    "admin": "admin123",
    "user1": "password1",
    "user2": "password2",
}


class LoginRequest(BaseModel):
    username: str
    password: str


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_sig = base64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid signature")
    payload_bytes = base64url_decode(payload_b64)
    payload = json.loads(payload_bytes)
    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token expired")
    return payload


def generate_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + TOKEN_EXPIRY_SECONDS),
    }
    return create_jwt(payload)


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header[7:]
    try:
        payload = decode_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return payload


@app.post("/login")
async def login(req: LoginRequest):
    if req.username not in USERS_DB or USERS_DB[req.username] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = generate_token(req.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }


@app.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello, {user['sub']}! You have access to this protected resource.",
        "user": user["sub"],
        "token_issued_at": user["iat"],
        "token_expires_at": user["exp"],
    }


@app.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    new_token = generate_token(user["sub"])
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
