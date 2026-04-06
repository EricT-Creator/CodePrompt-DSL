from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

class CalculatorInput(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]

class CalculatorResult(BaseModel):
    result: float

@app.post("/calculate", response_model=CalculatorResult)
async def calculate(input_data: CalculatorInput):
    if input_data.op == "add":
        result = input_data.a + input_data.b
    elif input_data.op == "sub":
        result = input_data.a - input_data.b
    elif input_data.op == "mul":
        result = input_data.a * input_data.b
    elif input_data.op == "div":
        if input_data.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero is not allowed")
        result = input_data.a / input_data.b
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    
    return CalculatorResult(result=result)