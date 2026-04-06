from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Calculator API")


class Operation(str, Enum):
    add = "add"
    sub = "sub"
    mul = "mul"
    div = "div"


class CalculationBody(BaseModel):
    a: float
    b: float
    op: Operation


@app.post("/calculate")
def calculate(body: CalculationBody) -> dict[str, float]:
    operations = {
        Operation.add: lambda left, right: left + right,
        Operation.sub: lambda left, right: left - right,
        Operation.mul: lambda left, right: left * right,
    }
    if body.op is Operation.div:
        if body.b == 0:
            raise HTTPException(status_code=400, detail="Cannot divide by zero")
        return {"result": body.a / body.b}
    return {"result": operations[body.op](body.a, body.b)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("BE-04_Calculator:app", host="127.0.0.1", port=8000, reload=False)
