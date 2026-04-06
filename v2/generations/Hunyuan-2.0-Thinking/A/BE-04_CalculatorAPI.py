from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class CalculateRequest(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]

@app.post("/calculate")
async def calculate(request: CalculateRequest):
    a = request.a
    b = request.b
    op = request.op
    
    if op == "add":
        result = a + b
    elif op == "sub":
        result = a - b
    elif op == "mul":
        result = a * b
    elif op == "div":
        if b == 0:
            return {"error": "Division by zero"}
        result = a / b
    else:
        return {"error": "Invalid operation"}
    
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)