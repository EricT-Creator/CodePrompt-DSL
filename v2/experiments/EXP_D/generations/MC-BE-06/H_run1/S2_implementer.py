import os
import os.path
import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

recent_queries = []


@app.post("/metadata")
def get_metadata(request_body: dict):
    paths = request_body.get("paths", [])
    results = []
    for p in paths:
        if not os.path.exists(p):
            results.append({"path": p, "error": "File not found"})
        else:
            results.append({
                "path": p,
                "size_bytes": os.path.getsize(p),
                "extension": os.path.splitext(p)[1],
                "modified_time": datetime.fromtimestamp(os.path.getmtime(p)).isoformat(),
                "is_directory": os.path.isdir(p),
            })
        if p in recent_queries:
            recent_queries.remove(p)
        recent_queries.insert(0, p)
    while len(recent_queries) > 10:
        recent_queries.pop()
    return results


@app.get("/recent")
def get_recent():
    return recent_queries


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
