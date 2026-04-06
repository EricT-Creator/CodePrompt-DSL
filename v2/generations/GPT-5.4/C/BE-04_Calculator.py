from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalculateInput(BaseModel):
    a: float
    b: float
    op: str


def add(left: float, right: float) -> float:
    return left + right


def sub(left: float, right: float) -> float:
    return left - right


def mul(left: float, right: float) -> float:
    return left * right


def div(left: float, right: float) -> float:
    if right == 0:
        raise HTTPException(status_code=400, detail="Division by zero")
    return left / right


OPERATORS: dict[str, Callable[[float, float], float]] = {
    "add": add,
    "sub": sub,
    "mul": mul,
    "div": div,
}


@app.post("/calculate")
def calculate(payload: CalculateInput) -> dict[str, float | str]:
    if payload.op not in OPERATORS:
        raise HTTPException(status_code=422, detail="Unsupported operation")
    return {"result": OPERATORS[payload.op](payload.a, payload.b), "op": payload.op}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
