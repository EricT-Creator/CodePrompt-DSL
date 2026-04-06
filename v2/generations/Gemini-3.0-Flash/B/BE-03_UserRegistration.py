from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, EmailStr
import re

app = FastAPI()

class User(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register", status_code=201)
def register(u: User):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", u.email):
        raise HTTPException(status_code=422, detail="Invalid email")
    if len(u.password) < 8:
        raise HTTPException(status_code=422, detail="Short password")
    return {"username": u.username, "email": u.email}
