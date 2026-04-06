from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

app = FastAPI()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

users_db: list[dict] = []

@app.post("/register", status_code=201)
def register(req: RegisterRequest):
    import re
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_pattern, req.email):
        raise HTTPException(status_code=422, detail="Invalid email format")
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    user = {"id": len(users_db) + 1, "username": req.username, "email": req.email}
    users_db.append(user)
    return user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
