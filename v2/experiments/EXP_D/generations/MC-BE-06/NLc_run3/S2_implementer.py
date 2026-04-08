import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

recently_accessed = []


@app.post("/metadata")
def inspect_files(data: dict):
    paths = data.get("paths", [])
    info = []
    for target in paths:
        if os.path.exists(target):
            ts = os.path.getmtime(target)
            info.append({
                "path": target,
                "size_bytes": os.path.getsize(target),
                "extension": os.path.splitext(target)[1],
                "modified_time": datetime.fromtimestamp(ts).isoformat(),
                "is_directory": os.path.isdir(target),
            })
        else:
            info.append({"path": target, "error": "File not found"})
        if target in recently_accessed:
            recently_accessed.remove(target)
        recently_accessed.insert(0, target)
    recently_accessed[:] = recently_accessed[:10]
    return info


@app.get("/recent")
def get_recent_queries():
    return recently_accessed


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
