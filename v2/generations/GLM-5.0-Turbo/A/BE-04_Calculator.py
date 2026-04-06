from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CalcRequest(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def calculate(req: CalcRequest):
    if req.op == "add":
        result = req.a + req.b
    elif req.op == "sub":
        result = req.a - req.b
    elif req.op == "mul":
        result = req.a * req.b
    elif req.op == "div":
        if req.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero is not allowed")
        result = req.a / req.b
    else:
        raise HTTPException(status_code=400, detail="Invalid operator. Use add, sub, mul, or div.")
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
