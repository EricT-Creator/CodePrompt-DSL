import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

path_history = []


@app.post("/metadata")
def collect_metadata(req: dict):
    paths = req.get("paths", [])
    output = []
    for item_path in paths:
        if not os.path.exists(item_path):
            output.append({"path": item_path, "error": "File not found"})
        else:
            mod_ts = os.path.getmtime(item_path)
            output.append({
                "path": item_path,
                "size_bytes": os.path.getsize(item_path),
                "extension": os.path.splitext(item_path)[1],
                "modified_time": datetime.fromtimestamp(mod_ts).isoformat(),
                "is_directory": os.path.isdir(item_path),
            })
        if item_path in path_history:
            path_history.remove(item_path)
        path_history.insert(0, item_path)
    while len(path_history) > 10:
        path_history.pop()
    return output


@app.get("/recent")
def recent_paths():
    return path_history


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
