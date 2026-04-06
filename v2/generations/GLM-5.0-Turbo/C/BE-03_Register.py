from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class RegisterBody(BaseModel):
    username: str
    email: str
    password: str

storage: list[dict] = []
_counter = 0

@app.post("/register", status_code=201)
def handle_register(body: RegisterBody):
    import re
    global _counter
    if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", body.email):
        raise HTTPException(422, {"error": "email_format_invalid"})
    if len(body.password) < 8:
        raise HTTPException(422, {"error": "password_too_short"})
    _counter += 1
    profile = {"id": _counter, "username": body.username, "email": body.email}
    storage.append({"id": _counter, "username": body.username, "email": body.email, "password": body.password})
    return profile

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
