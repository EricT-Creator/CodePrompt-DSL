import os
import os.path
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

recent_queries = []


@app.post("/metadata")
def post_metadata(data: dict):
    paths = data.get("paths", [])
    results = []
    for path_str in paths:
        if not os.path.exists(path_str):
            results.append({"path": path_str, "error": "File not found"})
        else:
            mod_time = os.path.getmtime(path_str)
            results.append({
                "path": path_str,
                "size_bytes": os.path.getsize(path_str),
                "extension": os.path.splitext(path_str)[1],
                "modified_time": datetime.fromtimestamp(mod_time).isoformat(),
                "is_directory": os.path.isdir(path_str),
            })
        if path_str in recent_queries:
            recent_queries.remove(path_str)
        recent_queries.insert(0, path_str)
    recent_queries[:] = recent_queries[:10]
    return results


@app.get("/recent")
def get_recent_paths():
    return recent_queries


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
