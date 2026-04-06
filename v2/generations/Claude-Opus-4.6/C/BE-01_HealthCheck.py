from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI()


@app.get("/health")
async def get_health():
    current_time = datetime.now(timezone.utc).isoformat()
    return {"status": "ok", "timestamp": current_time}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
