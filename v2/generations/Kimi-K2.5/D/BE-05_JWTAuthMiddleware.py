from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import hmac
import hashlib
import base64
import json
import time
from typing import Optional

app = FastAPI()

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY = 30 * 60  # 30 minutes in seconds

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)

def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_encoded = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    signature_encoded = base64url_encode(signature)
    return f"{message}.{signature_encoded}"

def verify_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_encoded, payload_encoded, signature_encoded = parts
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        expected_signature_encoded = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
            return None
        payload_json = base64url_decode(payload_encoded)
        payload = json.loads(payload_json)
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def refresh_jwt(payload: dict) -> str:
    new_payload = payload.copy()
    new_payload['iat'] = int(time.time())
    new_payload['exp'] = int(time.time()) + TOKEN_EXPIRY
    return create_jwt(new_payload)

@app.post("/login")
def login(username: str, password: str):
    if username == "admin" and password == "password":
        payload = {
            "sub": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_EXPIRY
        }
        token = create_jwt(payload)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/protected")
def protected(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]
    payload = verify_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": "Access granted", "user": payload.get("sub")}

@app.post("/refresh")
def refresh(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]
    payload = verify_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    new_token = refresh_jwt(payload)
    return {"access_token": new_token, "token_type": "bearer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
