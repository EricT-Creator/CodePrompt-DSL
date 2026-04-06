from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re
import uvicorn

app = FastAPI()

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str

    @validator('email')
    def validate_email_format(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v

    @validator('password')
    def validate_password_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    username: str
    email: str
    id: int

users_db = []
user_id_counter = 1

@app.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user: UserRegistration):
    try:
        # Validate the user data using Pydantic
        validated_user = UserRegistration(
            username=user.username,
            email=user.email,
            password=user.password
        )
        
        # Check if email already exists
        for existing_user in users_db:
            if existing_user['email'] == validated_user.email:
                raise HTTPException(
                    status_code=422,
                    detail="Email already registered"
                )
        
        # Create new user
        global user_id_counter
        new_user = {
            "id": user_id_counter,
            "username": validated_user.username,
            "email": validated_user.email,
            "password": validated_user.password  # In real app, this should be hashed
        }
        users_db.append(new_user)
        user_id_counter += 1
        
        # Return user info without password
        return UserResponse(
            id=new_user["id"],
            username=new_user["username"],
            email=new_user["email"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)