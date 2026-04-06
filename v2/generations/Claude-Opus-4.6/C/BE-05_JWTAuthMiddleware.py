import hashlib
import hmac
import base64
import json
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

SECRET_KEY = b"super-secret-key-for-jwt-signing-2026"
TOKEN_EXPIRY = 1800  # 30 minutes

USERS_DB = {
    "admin": "password123",
    "user": "pass456",
}


class LoginRequest(BaseModel):
    username: str
    password: str


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


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
    signature = hmac.new(SECRET_KEY, signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    return f"{signing_input}.{sig_b64}"


def decode_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(SECRET_KEY, signing_input.encode(), hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)
        if "exp" in payload and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


def extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth_header[7:]


async def get_current_user(request: Request) -> dict:
    token = extract_token(request)
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


@app.post("/login")
async def login(credentials: LoginRequest):
    if credentials.username not in USERS_DB:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if USERS_DB[credentials.username] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    now = time.time()
    payload = {
        "sub": credentials.username,
        "iat": int(now),
        "exp": int(now + TOKEN_EXPIRY),
    }
    token = create_jwt(payload)
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY}


@app.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello, {user['sub']}! You have access to this protected resource.",
        "user": user["sub"],
        "token_issued_at": user.get("iat"),
        "token_expires_at": user.get("exp"),
    }


@app.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    now = time.time()
    new_payload = {
        "sub": user["sub"],
        "iat": int(now),
        "exp": int(now + TOKEN_EXPIRY),
    }
    new_token = create_jwt(new_payload)
    return {"access_token": new_token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
