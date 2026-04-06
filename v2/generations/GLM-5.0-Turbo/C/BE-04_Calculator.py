from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class NumOp(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def calc(payload: NumOp):
    ops = {"add": float.__add__, "sub": float.__sub__, "mul": float.__mul__}
    if payload.op == "div":
        if payload.b == 0:
            raise HTTPException(400, "division by zero")
        return {"result": payload.a / payload.b}
    if payload.op not in ops:
        raise HTTPException(400, f"unknown op: {payload.op}")
    return {"result": ops[payload.op](payload.a, payload.b)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
