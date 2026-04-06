from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI()

class Register(BaseModel):
    username: str
    email: str
    password: str

class User(BaseModel):
    username: str
    email: str

def validate_email(email: str) -> bool:
    pattern = r'^[^@]+@[^@]+\.[^@]+$'
    return re.match(pattern, email) is not None

@app.post("/register")
def register(data: Register):
    if not validate_email(data.email):
        raise HTTPException(status_code=422, detail="Invalid email format")
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    return {"status": 201, "user": {"username": data.username, "email": data.email}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
