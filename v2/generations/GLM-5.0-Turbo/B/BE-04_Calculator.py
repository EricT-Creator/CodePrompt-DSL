from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CalculationInput(BaseModel):
    a: float
    b: float
    op: str

OPERATIONS = {
    "add": lambda x, y: x + y,
    "sub": lambda x, y: x - y,
    "mul": lambda x, y: x * y,
    "div": lambda x, y: x / y,
}

@app.post("/calculate")
def compute(data: CalculationInput):
    if data.op not in OPERATIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {data.op}")
    if data.op == "div" and data.b == 0:
        raise HTTPException(status_code=400, detail="Cannot divide by zero")
    value = OPERATIONS[data.op](data.a, data.b)
    return {"a": data.a, "b": data.b, "op": data.op, "result": value}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
