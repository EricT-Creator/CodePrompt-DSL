import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

recent_paths = []


@app.post("/metadata")
def query_metadata(body: dict):
    paths = body.get("paths", [])
    output = []
    for file_path in paths:
        if os.path.exists(file_path):
            output.append({
                "path": file_path,
                "size_bytes": os.path.getsize(file_path),
                "extension": os.path.splitext(file_path)[1],
                "modified_time": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                "is_directory": os.path.isdir(file_path),
            })
        else:
            output.append({"path": file_path, "error": "File not found"})
        if file_path in recent_paths:
            recent_paths.remove(file_path)
        recent_paths.insert(0, file_path)
    del recent_paths[10:]
    return output


@app.get("/recent")
def list_recent():
    return recent_paths


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
