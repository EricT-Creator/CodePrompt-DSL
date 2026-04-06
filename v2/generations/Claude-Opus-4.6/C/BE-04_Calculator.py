from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class MathOp(BaseModel):
    a: float
    b: float
    op: str


@app.post("/calculate")
async def calc(body: MathOp):
    if body.op == "add":
        return {"a": body.a, "b": body.b, "op": body.op, "result": body.a + body.b}
    elif body.op == "sub":
        return {"a": body.a, "b": body.b, "op": body.op, "result": body.a - body.b}
    elif body.op == "mul":
        return {"a": body.a, "b": body.b, "op": body.op, "result": body.a * body.b}
    elif body.op == "div":
        if body.b == 0:
            raise HTTPException(400, detail="Division by zero is not allowed")
        return {"a": body.a, "b": body.b, "op": body.op, "result": body.a / body.b}
    raise HTTPException(400, detail=f"Invalid operation: {body.op}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
