import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

app = FastAPI(title="Manual JWT Auth Middleware")

SECRET_KEY = b"codeprompt-dsl-demo-secret"
TOKEN_TTL_SECONDS = 30 * 60
USERS = {
    "demo": "password123",
    "admin": "admin123",
}
PROTECTED_ROUTES = {
    ("GET", "/protected"),
    ("POST", "/refresh"),
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_TTL_SECONDS


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def sign(signing_input: bytes) -> str:
    digest = hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest()
    return b64url_encode(digest)


def create_token(username: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }

    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = sign(signing_input)
    return f"{header_b64}.{payload_b64}.{signature}"


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise unauthorized("Malformed token")

    header_b64, payload_b64, signature = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = sign(signing_input)

    if not hmac.compare_digest(signature, expected_signature):
        raise unauthorized("Invalid signature")

    try:
        header = json.loads(b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise unauthorized("Invalid token payload") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise unauthorized("Unsupported token header")

    exp = payload.get("exp")
    sub = payload.get("sub")
    if not isinstance(exp, int) or not isinstance(sub, str):
        raise unauthorized("Invalid token claims")

    if exp < int(time.time()):
        raise unauthorized("Token expired")

    return payload


def extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise unauthorized("Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise unauthorized("Missing bearer token")
    return token


@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    route_key = (request.method.upper(), request.url.path)
    if route_key in PROTECTED_ROUTES:
        token = extract_bearer_token(request)
        request.state.jwt_payload = decode_token(token)
    return await call_next(request)


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": "Manual JWT auth demo",
        "available_users": sorted(USERS.keys()),
        "protected_routes": ["GET /protected", "POST /refresh"],
    }


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    expected_password = USERS.get(payload.username)
    if expected_password != payload.password:
        raise unauthorized("Invalid username or password")

    return TokenResponse(access_token=create_token(payload.username))


@app.get("/protected")
def protected(request: Request) -> Dict[str, Any]:
    payload = getattr(request.state, "jwt_payload", None)
    if not payload:
        raise unauthorized("Missing JWT payload")

    return {
        "message": "Access granted",
        "user": payload["sub"],
        "issued_at": payload["iat"],
        "expires_at": payload["exp"],
    }


@app.post("/refresh", response_model=TokenResponse)
def refresh(request: Request) -> TokenResponse:
    payload = getattr(request.state, "jwt_payload", None)
    if not payload:
        raise unauthorized("Missing JWT payload")

    return TokenResponse(access_token=create_token(payload["sub"]))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
