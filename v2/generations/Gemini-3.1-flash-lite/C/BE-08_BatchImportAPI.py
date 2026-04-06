from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import csv
import io

app = FastAPI()
data_store = []

@app.post("/import")
async def batch_import(file: UploadFile = File(...)):
    content = await file.read()
    stream = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(stream)
    
    success = 0
    failed = 0
    
    for row in reader:
        if row.get('name') and '@' in row.get('email', ''):
            data_store.append(row)
            success += 1
        else:
            failed += 1
    
    return {"total": success + failed, "success": success, "failed": failed}

@app.get("/data")
async def get_data():
    return data_store
