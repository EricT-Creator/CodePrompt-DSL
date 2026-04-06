from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr

app = FastAPI()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register", status_code=201)
def register(req: RegisterRequest):
    errors = []
    if "@" not in req.email or "." not in req.email:
        errors.append("Invalid email format")
    if len(req.password) < 8:
        errors.append("Password must be at least 8 characters long")
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)
    return {"username": req.username, "email": req.email}