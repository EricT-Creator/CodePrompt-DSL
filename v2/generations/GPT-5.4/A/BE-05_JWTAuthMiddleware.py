import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Manual JWT Auth")

SECRET_KEY = "change-this-secret-key"
TOKEN_TTL_SECONDS = 30 * 60
USERS = {
    "admin": "password123",
    "demo": "demo123",
}


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign(message: bytes) -> str:
    digest = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    return base64url_encode(digest)


def create_token(subject: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }

    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = sign(signing_input)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def decode_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    encoded_header, encoded_payload, received_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = sign(signing_input)

    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        header = json.loads(base64url_decode(encoded_header).decode("utf-8"))
        payload = json.loads(base64url_decode(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Malformed token") from None

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise HTTPException(status_code=401, detail="Unsupported token type")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Invalid subject")

    return payload


def extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return credentials.strip()


@app.post("/login")
async def login(payload: Dict[str, Any]) -> Dict[str, Any]:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if USERS.get(username) != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@app.get("/protected")
async def protected(request: Request) -> Dict[str, Any]:
    token = extract_bearer_token(request)
    payload = decode_token(token)
    return {
        "message": "Access granted",
        "user": payload["sub"],
        "expires_at": payload["exp"],
    }


@app.post("/refresh")
async def refresh(request: Request) -> Dict[str, Any]:
    token = extract_bearer_token(request)
    payload = decode_token(token)
    new_token = create_token(payload["sub"])
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@app.get("/")
async def index() -> Dict[str, str]:
    return {"message": "Use /login to obtain a JWT, then call /protected or /refresh."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
