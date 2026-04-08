import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

recent_paths_store = []


@app.post("/metadata")
def analyze_paths(request_data: dict):
    paths = request_data.get("paths", [])
    response = []
    for path_val in paths:
        if not os.path.exists(path_val):
            response.append({"path": path_val, "error": "File not found"})
        else:
            response.append({
                "path": path_val,
                "size_bytes": os.path.getsize(path_val),
                "extension": os.path.splitext(path_val)[1],
                "modified_time": datetime.fromtimestamp(
                    os.path.getmtime(path_val)
                ).isoformat(),
                "is_directory": os.path.isdir(path_val),
            })
        if path_val in recent_paths_store:
            recent_paths_store.remove(path_val)
        recent_paths_store.insert(0, path_val)
    recent_paths_store[:] = recent_paths_store[:10]
    return response


@app.get("/recent")
def show_recent():
    return recent_paths_store


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
