import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Manual JWT Auth")

SECRET_KEY = "codeprompt-dsl-gpt-5.4-manual-jwt-secret"
TOKEN_TTL_SECONDS = 30 * 60
USERS = {
    "admin": "admin123",
    "demo": "demo123",
}
PROTECTED_ROUTES = {("GET", "/protected"), ("POST", "/refresh")}


class TokenError(Exception):
    pass


def base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def sign(message: bytes) -> str:
    digest = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    return base64url_encode(digest)


def issue_token(subject: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    header_segment = base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_segment = base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = sign(signing_input)
    return f"{header_segment}.{payload_segment}.{signature}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenError("Invalid token format") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = sign(signing_input)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise TokenError("Invalid token signature")

    try:
        header = json.loads(base64url_decode(header_segment))
        payload = json.loads(base64url_decode(payload_segment))
    except (json.JSONDecodeError, ValueError) as exc:
        raise TokenError("Invalid token payload") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise TokenError("Unsupported token header")

    if not isinstance(payload.get("exp"), int) or not isinstance(payload.get("sub"), str):
        raise TokenError("Token payload missing required fields")

    if payload["exp"] <= int(time.time()):
        raise TokenError("Token expired")

    return payload


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise TokenError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise TokenError("Authorization header must use Bearer token")
    return token


@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
    if (request.method, request.url.path) not in PROTECTED_ROUTES:
        return await call_next(request)

    try:
        token = extract_bearer_token(request.headers.get("Authorization"))
        payload = decode_token(token)
        request.state.jwt_payload = payload
    except TokenError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return await call_next(request)


@app.post("/login")
async def login(credentials: dict[str, Any] = Body(...)):
    username = str(credentials.get("username", "")).strip()
    password = str(credentials.get("password", "")).strip()

    if not username or not password:
        return JSONResponse(status_code=401, content={"detail": "Username and password are required"})

    if USERS.get(username) != password:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    token = issue_token(username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@app.get("/protected")
async def protected(request: Request):
    payload = request.state.jwt_payload
    return {
        "message": "Access granted",
        "user": payload["sub"],
        "expires_at": payload["exp"],
    }


@app.post("/refresh")
async def refresh(request: Request):
    payload = request.state.jwt_payload
    new_token = issue_token(payload["sub"])
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@app.get("/")
async def index():
    return {
        "message": "Use POST /login to obtain a token, then access GET /protected or POST /refresh with Bearer auth.",
        "users": list(USERS.keys()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
