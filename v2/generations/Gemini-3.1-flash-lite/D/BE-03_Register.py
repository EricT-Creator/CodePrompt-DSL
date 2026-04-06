from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

# [语]Py[架]FastAPI[式]Mod[依]NoExt[数据]Mock[出]纯码
app = FastAPI()

@app.post("/register", status_code=201)
def 注册(用户名: str, 邮箱: EmailStr, 密码: str):
    if len(密码) < 8:
        raise HTTPException(422, "密码过短")
    return {"用户名": 用户名, "邮箱": 邮箱}
