from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()


class SignupPayload(BaseModel):
    username: str
    email: str
    password: str


class AccountService:
    def __init__(self) -> None:
        self._next_id = 1

    def is_valid_email(self, email: str) -> bool:
        local, separator, domain = email.partition("@")
        return bool(separator and local and "." in domain and not email.startswith("@") and not email.endswith("."))

    def create_user(self, payload: SignupPayload) -> dict[str, object]:
        if not self.is_valid_email(payload.email):
            raise HTTPException(status_code=422, detail="Invalid email format")
        if len(payload.password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters long")
        user = {"id": self._next_id, "username": payload.username, "email": payload.email}
        self._next_id += 1
        return user


service = AccountService()


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: SignupPayload) -> dict[str, object]:
    return service.create_user(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
