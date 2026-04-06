from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Req(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
async def run(r: Req):
    ops = {
        'add': lambda a, b: a + b,
        'sub': lambda a, b: a - b,
        'mul': lambda a, b: a * b,
        'div': lambda a, b: a / b if b != 0 else None
    }
    if r.op not in ops: raise HTTPException(400)
    res = ops[r.op](r.a, r.b)
    if res is None: raise HTTPException(400, "DivZero")
    return {"res": res}
