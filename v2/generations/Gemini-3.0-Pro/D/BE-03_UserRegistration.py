from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr

app = FastAPI()

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: constr(min_length=8)

class UserRegisterResponse(BaseModel):
    username: str
    email: str

@app.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegisterRequest):
    return UserRegisterResponse(username=user.username, email=user.email)
