import os
import os.path
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

recent_list = []


@app.post("/metadata")
def retrieve_metadata(body: dict):
    paths = body.get("paths", [])
    result = []
    for p in paths:
        if os.path.exists(p):
            mtime = os.path.getmtime(p)
            result.append({
                "path": p,
                "size_bytes": os.path.getsize(p),
                "extension": os.path.splitext(p)[1],
                "modified_time": datetime.fromtimestamp(mtime).isoformat(),
                "is_directory": os.path.isdir(p),
            })
        else:
            result.append({"path": p, "error": "File not found"})
        if p in recent_list:
            recent_list.remove(p)
        recent_list.insert(0, p)
    while len(recent_list) > 10:
        recent_list.pop()
    return result


@app.get("/recent")
def get_recent():
    return recent_list


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
