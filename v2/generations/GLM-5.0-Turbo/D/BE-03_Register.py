from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class RegisterInput(BaseModel):
    username: str
    email: str
    password: str

user_store: list[dict] = []

@app.post("/register", status_code=201)
def register(input_data: RegisterInput):
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, input_data.email):
        raise HTTPException(status_code=422, detail="邮箱格式不合法")
    if len(input_data.password) < 8:
        raise HTTPException(status_code=422, detail="密码长度不足八位")
    uid = len(user_store) + 1
    user_store.append({"id": uid, "username": input_data.username, "email": input_data.email, "password": input_data.password})
    return {"id": uid, "username": input_data.username, "email": input_data.email}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
