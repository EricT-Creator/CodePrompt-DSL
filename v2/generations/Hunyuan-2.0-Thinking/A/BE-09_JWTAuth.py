from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import hmac
import base64
import json
import time

app = FastAPI()
security = HTTPBearer()

# Mock user
VALID_USER = {"username": "admin", "password": "password123"}

# Simple JWT-like token generation (for demo purposes)
def generate_token(username: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"username": username, "exp": int(time.time()) + 3600}
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    signature = hmac.new(
        b"secret_key",
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split('.')
        
        # Verify signature
        expected_sig = hmac.new(
            b"secret_key",
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        
        actual_sig = base64.urlsafe_b64decode(signature_b64 + "==")
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
        
        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except:
        return None

@app.post("/login")
async def login(username: str, password: str):
    if username == VALID_USER["username"] and password == VALID_USER["password"]:
        token = generate_token(username)
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload:
        return {"user": payload["username"], "message": "Access granted"}
    raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)