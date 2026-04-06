from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class HealthResponse(BaseModel):
    status: str


class WelcomeResponse(BaseModel):
    message: str


@app.get("/", response_model=WelcomeResponse)
def read_root():
    return {"message": "Welcome"}


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
