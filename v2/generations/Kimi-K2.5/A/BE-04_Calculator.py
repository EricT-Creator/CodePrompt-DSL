from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CalculateRequest(BaseModel):
    a: float
    b: float
    op: str

class CalculateResponse(BaseModel):
    result: float

@app.post("/calculate")
def calculate(req: CalculateRequest):
    if req.op == "add":
        result = req.a + req.b
    elif req.op == "sub":
        result = req.a - req.b
    elif req.op == "mul":
        result = req.a * req.b
    elif req.op == "div":
        if req.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        result = req.a / req.b
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    
    return {"result": result}
