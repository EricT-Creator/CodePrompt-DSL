from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import uuid

app = FastAPI()

user_store: list[dict] = []


class RegisterInput(BaseModel):
    username: str
    email: str
    password: str


@app.post("/register", status_code=201)
async def register(data: RegisterInput):
    problems = []
    if not re.match(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$", data.email):
        problems.append("Email format invalid")
    if len(data.password) < 8:
        problems.append("Password must contain at least 8 characters")
    if problems:
        raise HTTPException(status_code=422, detail=problems)
    new_user = {
        "id": str(uuid.uuid4()),
        "username": data.username,
        "email": data.email,
    }
    user_store.append(new_user)
    return new_user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
