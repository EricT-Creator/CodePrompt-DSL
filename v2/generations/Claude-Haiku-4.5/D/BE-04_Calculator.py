from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Calculate(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def calculate(data: Calculate):
    if data.op == "add":
        return {"result": data.a + data.b}
    elif data.op == "sub":
        return {"result": data.a - data.b}
    elif data.op == "mul":
        return {"result": data.a * data.b}
    elif data.op == "div":
        if data.b == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        return {"result": data.a / data.b}
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
