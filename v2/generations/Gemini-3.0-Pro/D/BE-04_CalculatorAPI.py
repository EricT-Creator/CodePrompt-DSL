from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal, Union

app = FastAPI()

class CalculateRequest(BaseModel):
    a: Union[int, float]
    b: Union[int, float]
    op: Literal["add", "sub", "mul", "div"]

class CalculateResponse(BaseModel):
    result: Union[int, float]

@app.post("/calculate", response_model=CalculateResponse)
async def calculate(request: CalculateRequest):
    if request.op == "add":
        return CalculateResponse(result=request.a + request.b)
    elif request.op == "sub":
        return CalculateResponse(result=request.a - request.b)
    elif request.op == "mul":
        return CalculateResponse(result=request.a * request.b)
    elif request.op == "div":
        if request.b == 0:
            raise HTTPException(status_code=400, detail="不可除零")
        return CalculateResponse(result=request.a / request.b)
