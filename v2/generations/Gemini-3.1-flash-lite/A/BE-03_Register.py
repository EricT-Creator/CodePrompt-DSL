from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()

class User(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=8)

@app.post("/register", status_code=201)
def register(user: User):
    return {"username": user.username, "email": user.email}
