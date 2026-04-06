import re

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()
email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
registered_users: list[dict[str, object]] = []


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class RegisterResponse(BaseModel):
    id: int
    username: str
    email: str


@app.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest) -> RegisterResponse:
    if not email_pattern.fullmatch(payload.email):
        raise HTTPException(status_code=422, detail={"field": "email", "message": "Invalid email format"})
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail={"field": "password", "message": "Password must be at least 8 characters"})
    user = {"id": len(registered_users) + 1, "username": payload.username, "email": payload.email}
    registered_users.append(user)
    return RegisterResponse(**user)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
