from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class CalcRequest(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]

@app.post("/calculate")
def calculate(req: CalcRequest):
    if req.op == "add": return {"result": req.a + req.b}
    if req.op == "sub": return {"result": req.a - req.b}
    if req.op == "mul": return {"result": req.a * req.b}
    if req.op == "div":
        if req.b == 0: raise HTTPException(400, "Division by zero")
        return {"result": req.a / req.b}
