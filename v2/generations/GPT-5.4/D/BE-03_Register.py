from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
users: list[dict[str, object]] = []


class RegisterBody(BaseModel):
    username: str
    email: str
    password: str


def check_email(email: str) -> bool:
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or not domain or "." not in domain:
        return False
    if any(char.isspace() for char in email):
        return False
    return True


@app.post("/register", status_code=201)
def register(body: RegisterBody) -> dict[str, object]:
    if not check_email(body.email):
        raise HTTPException(status_code=422, detail={"error": "Invalid email format"})
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail={"error": "Password is too short"})
    user = {"id": len(users) + 1, "username": body.username, "email": body.email}
    users.append(user)
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
