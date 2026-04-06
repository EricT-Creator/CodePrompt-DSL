from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import uuid

app = FastAPI()

users: list[dict] = []


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@app.post("/register", status_code=201)
async def register(req: RegisterRequest):
    errors = []
    email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, req.email):
        errors.append("Invalid email format")
    if len(req.password) < 8:
        errors.append("Password must be at least 8 characters")
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    user = {
        "id": str(uuid.uuid4()),
        "username": req.username,
        "email": req.email,
    }
    users.append(user)
    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
