import hmac
import hashlib
import base64
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 30 * 60

USERS_DB = {
    "admin": "password123",
    "user": "userpass",
}


class LoginRequest(BaseModel):
    username: str
    password: str


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload: dict) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        actual_signature = base64url_decode(signature_b64)
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)
        if "exp" in payload and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


@app.post("/login")
def login(req: LoginRequest):
    if req.username not in USERS_DB or USERS_DB[req.username] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = time.time()
    payload = {
        "sub": req.username,
        "iat": int(now),
        "exp": int(now + TOKEN_EXPIRY_SECONDS),
    }
    token = create_jwt(payload)
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY_SECONDS}


@app.get("/protected")
def protected(user: dict = Depends(get_current_user)):
    return {"message": f"Hello, {user['sub']}! You have access to this protected resource.", "user": user["sub"]}


@app.post("/refresh")
def refresh(user: dict = Depends(get_current_user)):
    now = time.time()
    payload = {
        "sub": user["sub"],
        "iat": int(now),
        "exp": int(now + TOKEN_EXPIRY_SECONDS),
    }
    token = create_jwt(payload)
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY_SECONDS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
