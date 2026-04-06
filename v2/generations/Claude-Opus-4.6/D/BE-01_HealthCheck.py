from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI()


@app.get("/health")
async def health_check():
    now = datetime.now(timezone.utc)
    return {
        "status": "ok",
        "timestamp": now.isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
