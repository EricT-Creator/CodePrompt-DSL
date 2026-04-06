from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CalcBody(BaseModel):
    a: float
    b: float
    op: str


@app.post("/calculate")
def calculate(body: CalcBody) -> dict[str, float]:
    match body.op:
        case "add":
            result = body.a + body.b
        case "sub":
            result = body.a - body.b
        case "mul":
            result = body.a * body.b
        case "div":
            if body.b == 0:
                raise HTTPException(status_code=400, detail="Division by zero")
            result = body.a / body.b
        case _:
            raise HTTPException(status_code=422, detail="op must be one of add, sub, mul, div")
    return {"result": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
