from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Union

app = FastAPI()

class CalculationRequest(BaseModel):
    a: Union[int, float]
    b: Union[int, float]
    op: Literal["add", "sub", "mul", "div"]

class CalculationResponse(BaseModel):
    result: Union[int, float]

@app.post("/calculate", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    if request.op == "add":
        result = request.a + request.b
    elif request.op == "sub":
        result = request.a - request.b
    elif request.op == "mul":
        result = request.a * request.b
    elif request.op == "div":
        if request.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero is not allowed.")
        result = request.a / request.b
    
    return CalculationResponse(result=result)
