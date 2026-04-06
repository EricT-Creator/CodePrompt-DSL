import csv
import io
import re
from fastapi import FastAPI, UploadFile, File
from starlette.responses import StreamingResponse

app = FastAPI()

db = []

def is_valid(row):
    return row['name'] and re.match(r"[^@]+@[^@]+\.[^@]+", row['email']) and 0 <= int(row['age']) <= 150

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    reader = csv.DictReader(io.StringIO((await file.read()).decode()))
    results = []
    
    async def generate():
        for row in reader:
            if is_valid(row):
                db.append(row)
                yield f"Row {row['name']} Success\n"
            else:
                yield f"Row {row.get('name', 'unknown')} Failed\n"
                
    return StreamingResponse(generate())

@app.get("/data")
def get_data():
    return db
