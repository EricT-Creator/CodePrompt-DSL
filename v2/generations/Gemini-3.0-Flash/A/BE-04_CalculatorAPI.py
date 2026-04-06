from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class CalcRequest(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]

@app.post("/calculate")
async def calculate(request: CalcRequest):
    if request.op == "add":
        return {"result": request.a + request.b}
    elif request.op == "sub":
        return {"result": request.a - request.b}
    elif request.op == "mul":
        return {"result": request.a * request.b}
    elif request.op == "div":
        if request.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        return {"result": request.a / request.b}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
