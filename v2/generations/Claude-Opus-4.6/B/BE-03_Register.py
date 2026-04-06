from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import uuid

app = FastAPI()

registered_users: list[dict] = []


class RegistrationPayload(BaseModel):
    username: str
    email: str
    password: str


@app.post("/register", status_code=201)
async def register_user(payload: RegistrationPayload):
    validation_errors = []
    if not re.match(r"^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$", payload.email):
        validation_errors.append("Email format is invalid")
    if len(payload.password) < 8:
        validation_errors.append("Password must be at least 8 characters long")
    if validation_errors:
        raise HTTPException(status_code=422, detail=validation_errors)
    user_record = {
        "id": str(uuid.uuid4()),
        "username": payload.username,
        "email": payload.email,
    }
    registered_users.append(user_record)
    return user_record


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
