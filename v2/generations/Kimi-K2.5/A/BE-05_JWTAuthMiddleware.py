import hmac
import hashlib
import base64
import json
import time
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY = 30 * 60  # 30 minutes in seconds

users_db = {
    "admin": "password123",
    "user": "mypassword"
}

class LoginRequest(BaseModel):
    username: str
    password: str


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('ascii'))


def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_encoded = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    
    return f"{message}.{signature_encoded}"


def verify_jwt(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_encoded = base64url_encode(expected_signature)
        
        if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
            raise ValueError("Invalid signature")
        
        payload = json.loads(base64url_decode(payload_encoded))
        
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")
        
        return payload
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")


async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    try:
        payload = verify_jwt(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/login")
async def login(request: LoginRequest):
    if request.username not in users_db:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if users_db[request.username] != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    payload = {
        "sub": request.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    token = create_jwt(payload)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)):
    return {"message": f"Hello {user['sub']}! This is a protected resource.", "user": user}


@app.post("/refresh")
async def refresh(user: dict = Depends(get_current_user)):
    payload = {
        "sub": user["sub"],
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    new_token = create_jwt(payload)
    return {"access_token": new_token, "token_type": "bearer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
