import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Registration API")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class RegistrationBody(BaseModel):
    username: str
    email: str
    password: str


class PublicUser(BaseModel):
    username: str
    email: str


def validate_registration(body: RegistrationBody) -> None:
    errors: list[dict[str, str]] = []
    if not EMAIL_RE.fullmatch(body.email):
        errors.append({"field": "email", "message": "Email format is invalid"})
    if len(body.password) < 8:
        errors.append({"field": "password", "message": "Password must be at least 8 characters long"})
    if errors:
        raise HTTPException(status_code=422, detail=errors)


@app.post("/register", response_model=PublicUser, status_code=201)
def register(body: RegistrationBody) -> PublicUser:
    validate_registration(body)
    return PublicUser(username=body.username, email=body.email)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("BE-03_Register:app", host="127.0.0.1", port=8000, reload=False)
