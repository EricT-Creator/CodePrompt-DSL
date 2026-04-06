from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
import uvicorn

app = FastAPI()

class CalculationRequest(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]

class CalculationResponse(BaseModel):
    result: float

@app.post("/calculate", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        if request.op == "add":
            result = request.a + request.b
        elif request.op == "sub":
            result = request.a - request.b
        elif request.op == "mul":
            result = request.a * request.b
        elif request.op == "div":
            if request.b == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Division by zero is not allowed"
                )
            result = request.a / request.b
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operator: {request.op}"
            )
        
        return CalculationResponse(result=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)