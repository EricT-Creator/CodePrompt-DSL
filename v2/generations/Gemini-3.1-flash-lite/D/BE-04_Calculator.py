from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# [语]Py[架]FastAPI[式]Mod[依]NoExt[数据]Mock[出]纯码
app = FastAPI()

class Req(BaseModel):
    a: float; b: float; 算: str

@app.post("/calculate")
def 计算(req: Req):
    if req.算 == "add": return {"res": req.a + req.b}
    if req.算 == "sub": return {"res": req.a - req.b}
    if req.算 == "mul": return {"res": req.a * req.b}
    if req.算 == "div":
        if req.b == 0: raise HTTPException(400, "除零错")
        return {"res": req.a / req.b}
