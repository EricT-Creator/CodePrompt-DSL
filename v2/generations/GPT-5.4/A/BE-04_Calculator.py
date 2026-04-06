from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalculationRequest(BaseModel):
    a: float
    b: float
    op: Literal["add", "sub", "mul", "div"]


@app.post("/calculate")
def calculate(payload: CalculationRequest) -> dict[str, float | str]:
    if payload.op == "add":
        result = payload.a + payload.b
    elif payload.op == "sub":
        result = payload.a - payload.b
    elif payload.op == "mul":
        result = payload.a * payload.b
    else:
        if payload.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        result = payload.a / payload.b
    return {"result": result, "operation": payload.op}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
