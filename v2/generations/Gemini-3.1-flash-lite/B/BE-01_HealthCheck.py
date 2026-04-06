from fastapi import FastAPI
from datetime import datetime

# Constraint: { "framework": "FastAPI", "language": "Python" }
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
