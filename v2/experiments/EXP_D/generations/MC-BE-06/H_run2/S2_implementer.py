import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

recently_queried = []


@app.post("/metadata")
def fetch_file_metadata(payload: dict):
    path_list = payload.get("paths", [])
    metadata_results = []
    for fp in path_list:
        if os.path.exists(fp):
            metadata_results.append({
                "path": fp,
                "size_bytes": os.path.getsize(fp),
                "extension": os.path.splitext(fp)[1],
                "modified_time": datetime.fromtimestamp(os.path.getmtime(fp)).isoformat(),
                "is_directory": os.path.isdir(fp),
            })
        else:
            metadata_results.append({"path": fp, "error": "File not found"})
        if fp in recently_queried:
            recently_queried.remove(fp)
        recently_queried.insert(0, fp)
    del recently_queried[10:]
    return metadata_results


@app.get("/recent")
def recent_queries():
    return recently_queried


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
