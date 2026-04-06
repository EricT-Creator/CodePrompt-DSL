import json
import base64
import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="JWT Auth API")

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY = 1800

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ProtectedResponse(BaseModel):
    message: str
    user: str
    exp: int

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)

def hmac_sha256_sign(message: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64url_encode(signature)

def create_jwt(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    
    header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_encoded = base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac_sha256_sign(message, SECRET_KEY)
    
    return f"{message}.{signature}"

def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature = parts
        
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac_sha256_sign(message, SECRET_KEY)
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        payload_json = base64url_decode(payload_encoded)
        payload = json.loads(payload_json)
        
        return payload
    except Exception:
        return None

def verify_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    payload = decode_jwt(token)
    
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise HTTPException(status_code=401, detail="Token expired")
    
    return payload

@app.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    if credentials.username != "admin" or credentials.password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    payload = {
        "sub": credentials.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    token = create_jwt(payload)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRY
    )

@app.get("/protected", response_model=ProtectedResponse)
async def protected(payload: Dict[str, Any] = Depends(verify_token)):
    return ProtectedResponse(
        message="Access granted to protected resource",
        user=payload.get("sub", "unknown"),
        exp=payload.get("exp", 0)
    )

@app.post("/refresh", response_model=TokenResponse)
async def refresh(payload: Dict[str, Any] = Depends(verify_token)):
    new_payload = {
        "sub": payload.get("sub", "unknown"),
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    new_token = create_jwt(new_payload)
    
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRY
    )

@app.get("/")
async def root():
    return {"message": "JWT Auth API", "endpoints": ["/login", "/protected", "/refresh"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
