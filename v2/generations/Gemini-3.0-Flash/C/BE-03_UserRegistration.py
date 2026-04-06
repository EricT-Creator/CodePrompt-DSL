from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI()

class Reg(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register", status_code=201)
async def signup(r: Reg):
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", r.email):
        raise HTTPException(422, "Email error")
    if len(r.password) < 8:
        raise HTTPException(422, "Password too short")
    return {"username": r.username, "email": r.email}
