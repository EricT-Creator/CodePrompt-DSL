from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str

registered_users: list[dict] = []

def is_valid_email(addr: str) -> bool:
    import re
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", addr))

@app.post("/register", status_code=201)
def register_user(data: UserRegistration):
    errors = []
    if not is_valid_email(data.email):
        errors.append({"field": "email", "message": "Invalid email format"})
    if len(data.password) < 8:
        errors.append({"field": "password", "message": "Password must be at least 8 characters long"})
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    user_id = len(registered_users) + 1
    result = {"id": user_id, "username": data.username, "email": data.email}
    registered_users.append({**result, "password": data.password})
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
