from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalculationInput(BaseModel):
    a: float
    b: float
    op: str


@app.post("/calculate")
async def perform_calculation(data: CalculationInput):
    operations = {
        "add": lambda x, y: x + y,
        "sub": lambda x, y: x - y,
        "mul": lambda x, y: x * y,
    }
    if data.op == "div":
        if data.b == 0:
            raise HTTPException(status_code=400, detail="Cannot divide by zero")
        return {"a": data.a, "b": data.b, "op": data.op, "result": data.a / data.b}
    if data.op not in operations:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {data.op}")
    result = operations[data.op](data.a, data.b)
    return {"a": data.a, "b": data.b, "op": data.op, "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
