from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

app = FastAPI()

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    
    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

users_db = []
user_id_counter = 1

@app.post("/register", status_code=201, response_model=UserResponse)
async def register(user: UserRegister):
    global user_id_counter
    
    new_user = {
        "id": user_id_counter,
        "username": user.username,
        "email": user.email,
        "password": user.password
    }
    users_db.append(new_user)
    user_id_counter += 1
    
    return UserResponse(
        id=new_user["id"],
        username=new_user["username"],
        email=new_user["email"]
    )