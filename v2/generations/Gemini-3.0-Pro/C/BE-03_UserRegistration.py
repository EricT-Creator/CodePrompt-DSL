from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr

app = FastAPI()

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: constr(min_length=8)

class UserResponse(BaseModel):
    username: str
    email: EmailStr

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    # In a real application, you would hash the password and save the user here
    return UserResponse(username=user.username, email=user.email)
