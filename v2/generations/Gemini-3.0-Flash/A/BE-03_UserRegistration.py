from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator
import re

app = FastAPI()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @validator('email')
    def validate_email(cls, v):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError('Invalid email format')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    username: str
    email: str

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    # Success returns 201 and user info
    return UserResponse(username=request.username, email=request.email)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
