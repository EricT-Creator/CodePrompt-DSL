from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Calc(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def calc(c: Calc):
    if c.op == 'add': return {"result": c.a + c.b}
    if c.op == 'sub': return {"result": c.a - c.b}
    if c.op == 'mul': return {"result": c.a * c.b}
    if c.op == 'div':
        if c.b == 0: raise HTTPException(400, "Division by zero")
        return {"result": c.a / c.b}
    raise HTTPException(400, "Invalid op")
