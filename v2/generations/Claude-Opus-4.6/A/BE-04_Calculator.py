from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalcRequest(BaseModel):
    a: float
    b: float
    op: str


@app.post("/calculate")
async def calculate(req: CalcRequest):
    if req.op == "add":
        result = req.a + req.b
    elif req.op == "sub":
        result = req.a - req.b
    elif req.op == "mul":
        result = req.a * req.b
    elif req.op == "div":
        if req.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        result = req.a / req.b
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {req.op}")
    return {"a": req.a, "b": req.b, "op": req.op, "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
