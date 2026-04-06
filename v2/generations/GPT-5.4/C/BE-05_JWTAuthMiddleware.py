import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request

app = FastAPI(title="Manual JWT Auth Middleware")

SECRET_KEY = b"gpt-5-4-exp-a-jwt-secret"
TOKEN_TTL_SECONDS = 30 * 60
USER_STORE = {
    "admin": "password123",
    "reviewer": "review456",
}
PROTECTED_PATHS = {"/protected", "/refresh"}


def base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def base64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def encode_part(data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64url_encode(payload)


def sign_input(signing_input: str) -> str:
    signature = hmac.new(SECRET_KEY, signing_input.encode("ascii"), hashlib.sha256).digest()
    return base64url_encode(signature)


def create_token(subject: str) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + TOKEN_TTL_SECONDS,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{encode_part(header)}.{encode_part(payload)}"
    return f"{signing_input}.{sign_input(signing_input)}"


def verify_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    signing_input = f"{parts[0]}.{parts[1]}"
    provided_signature = parts[2]
    expected_signature = sign_input(signing_input)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(base64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    expires_at = payload.get("exp")
    subject = payload.get("sub")
    if not isinstance(expires_at, int) or not isinstance(subject, str):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    if expires_at <= int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def extract_bearer_token(request: Request) -> str:
    header_value = request.headers.get("Authorization", "")
    if not header_value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return header_value[7:].strip()


@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    if request.url.path in PROTECTED_PATHS:
        token = extract_bearer_token(request)
        request.state.user = verify_token(token)
    response = await call_next(request)
    return response


@app.post("/login")
async def login(payload: dict[str, Any] = Body(...)):
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))
    if USER_STORE.get(username) != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "token": create_token(username),
        "expires_in": TOKEN_TTL_SECONDS,
        "token_type": "bearer",
    }


@app.get("/protected")
async def protected(request: Request):
    user = request.state.user
    return {
        "message": "Protected resource granted",
        "user": user["sub"],
        "issued_at": user["iat"],
        "expires_at": user["exp"],
    }


@app.post("/refresh")
async def refresh(request: Request):
    user = request.state.user
    return {
        "token": create_token(user["sub"]),
        "expires_in": TOKEN_TTL_SECONDS,
        "token_type": "bearer",
    }


@app.get("/")
async def root():
    return {"service": "manual-jwt-auth", "protected_paths": sorted(PROTECTED_PATHS)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
