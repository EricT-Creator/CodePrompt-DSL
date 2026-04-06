from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

app = FastAPI()

class User(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/register", status_code=201)
def reg(user: User):
    if len(user.password) < 8:
        raise HTTPException(422, "Password too short")
    return {"user": user.username, "email": user.email}
