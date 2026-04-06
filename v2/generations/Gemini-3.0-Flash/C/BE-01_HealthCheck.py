from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/health")
async def check():
    return {"status": "ok", "timestamp": time.ctime()}
