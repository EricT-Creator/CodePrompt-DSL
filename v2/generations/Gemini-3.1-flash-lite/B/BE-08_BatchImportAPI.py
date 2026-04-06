import csv
import io
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

app = FastAPI()

class Item(BaseModel):
    name: str
    email: EmailStr
    age: int

data_store = []

@app.post("/import")
async def batch_import(file: UploadFile = File(...)):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    
    results = []
    summary = {"total": 0, "success": 0, "failed": 0}
    
    for row in reader:
        summary["total"] += 1
        try:
            item = Item(**row)
            data_store.append(item.dict())
            results.append(f"Row {summary['total']}: OK\n")
            summary["success"] += 1
        except Exception as e:
            results.append(f"Row {summary['total']}: Error {str(e)}\n")
            summary["failed"] += 1
            
    results.append(f"Summary: {summary}")
    return StreamingResponse(iter(results), media_type="text/plain")

@app.get("/data")
def get_data():
    return data_store
