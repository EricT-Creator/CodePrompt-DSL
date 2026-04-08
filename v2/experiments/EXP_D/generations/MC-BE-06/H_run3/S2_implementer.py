import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

query_history = []


@app.post("/metadata")
def get_file_metadata(input_data: dict):
    paths = input_data.get("paths", [])
    metadata = []
    for fpath in paths:
        if os.path.exists(fpath):
            metadata.append({
                "path": fpath,
                "size_bytes": os.path.getsize(fpath),
                "extension": os.path.splitext(fpath)[1],
                "modified_time": datetime.fromtimestamp(
                    os.path.getmtime(fpath)
                ).isoformat(),
                "is_directory": os.path.isdir(fpath),
            })
        else:
            metadata.append({"path": fpath, "error": "File not found"})
        if fpath in query_history:
            query_history.remove(fpath)
        query_history.insert(0, fpath)
    del query_history[10:]
    return metadata


@app.get("/recent")
def recent():
    return query_history


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
