from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

# [L]Py[F]FastAPI[S]None[D]NoExt
app = FastAPI()

@app.post("/register", status_code=201)
def reg(name: str, email: EmailStr, pwd: str):
    if len(pwd) < 8:
        raise HTTPException(422)
    return {"name": name, "email": email}
