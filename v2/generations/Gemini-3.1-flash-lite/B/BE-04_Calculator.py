from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Req(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def calc(req: Req):
    if req.op == "add": return {"res": req.a + req.b}
    if req.op == "sub": return {"res": req.a - req.b}
    if req.op == "mul": return {"res": req.a * req.b}
    if req.op == "div":
        if req.b == 0: raise HTTPException(400)
        return {"res": req.a / req.b}
