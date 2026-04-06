from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, validator
import re

app = FastAPI()

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

    @validator('email')
    def validate_email(cls, v):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponse(BaseModel):
    username: str
    email: str

@app.post("/register")
def register(user: UserRegister):
    try:
        return {"username": user.username, "email": user.email}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
