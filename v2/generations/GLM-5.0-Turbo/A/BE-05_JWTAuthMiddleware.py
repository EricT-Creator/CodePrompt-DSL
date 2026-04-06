import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

SECRET_KEY = "my-super-secret-key-2026"
TOKEN_EXPIRY_SECONDS = 30 * 60  # 30 minutes


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_sig = b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth[7:]


# --- Models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    token: str


# --- Users DB (in-memory) ---

USERS_DB = {
    "admin": "password123",
    "user1": "hello456",
    "testuser": "test789",
}


# --- Endpoints ---

@app.post("/login")
async def login(req: LoginRequest):
    if req.username not in USERS_DB or USERS_DB[req.username] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    payload = {
        "sub": req.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }
    token = create_jwt(payload)
    return {"token": token, "expires_in": TOKEN_EXPIRY_SECONDS}


@app.get("/protected")
async def protected(token: str = Depends(get_bearer_token)):
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"message": f"Hello, {payload['sub']}!", "payload": payload}


@app.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = decode_jwt(req.token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    new_payload = {
        "sub": payload["sub"],
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }
    new_token = create_jwt(new_payload)
    return {"token": new_token, "expires_in": TOKEN_EXPIRY_SECONDS}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={"detail": exc.detail, "error": "Unauthorized"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
