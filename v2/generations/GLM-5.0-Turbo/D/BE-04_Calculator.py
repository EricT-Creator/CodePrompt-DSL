from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ComputeInput(BaseModel):
    a: float
    b: float
    op: str

@app.post("/calculate")
def do_calculate(inp: ComputeInput):
    if inp.op == "add":
        ans = inp.a + inp.b
    elif inp.op == "sub":
        ans = inp.a - inp.b
    elif inp.op == "mul":
        ans = inp.a * inp.b
    elif inp.op == "div":
        if inp.b == 0:
            raise HTTPException(status_code=400, detail="除零错误")
        ans = inp.a / inp.b
    else:
        raise HTTPException(status_code=400, detail="未知运算符")
    return {"result": ans}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
