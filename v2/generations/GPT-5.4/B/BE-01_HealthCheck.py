from datetime import datetime

from fastapi import FastAPI

app = FastAPI(title="Health API")


def iso_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": iso_timestamp()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("BE-01_HealthCheck:app", host="0.0.0.0", port=8000, reload=False)
