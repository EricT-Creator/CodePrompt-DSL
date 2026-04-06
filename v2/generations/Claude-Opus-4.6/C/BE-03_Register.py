from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import uuid

app = FastAPI()

_users: list[dict] = []


class RegBody(BaseModel):
    username: str
    email: str
    password: str


@app.post("/register", status_code=201)
async def register(body: RegBody):
    errs = []
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}", body.email):
        errs.append("Invalid email")
    if len(body.password) < 8:
        errs.append("Password too short (min 8)")
    if errs:
        raise HTTPException(422, detail=errs)
    user = {"id": str(uuid.uuid4()), "username": body.username, "email": body.email}
    _users.append(user)
    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
