from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI()

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register")
async def register(user: UserRegister):
    # 验证邮箱格式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user.email):
        raise HTTPException(status_code=422, detail="邮箱格式有误")
    
    # 验证密码长度
    if len(user.password) < 8:
        raise HTTPException(status_code=422, detail="密码至少八位")
    
    # 返回用户信息（不含密码）
    return {
        "message": "注册成功",
        "user": {
            "username": user.username,
            "email": user.email
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)