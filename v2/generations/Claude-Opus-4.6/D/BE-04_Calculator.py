from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalcBody(BaseModel):
    a: float
    b: float
    op: str


_ops = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
}


@app.post("/calculate")
async def calculate(body: CalcBody):
    if body.op == "div":
        if body.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero error")
        return {"a": body.a, "b": body.b, "op": "div", "result": body.a / body.b}
    fn = _ops.get(body.op)
    if fn is None:
        raise HTTPException(status_code=400, detail=f"Unknown operator: {body.op}")
    return {"a": body.a, "b": body.b, "op": body.op, "result": fn(body.a, body.b)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
