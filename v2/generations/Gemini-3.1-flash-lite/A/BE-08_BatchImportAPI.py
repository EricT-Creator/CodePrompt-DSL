from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import csv
import io
import re

app = FastAPI()

# In-memory storage
data_store = {}

def is_valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

@app.post("/upload")
async def batch_upload(file: UploadFile = File(...)):
    content = await file.read()
    stream = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(stream)
    
    success_count = 0
    failure_count = 0
    skipped_count = 0
    errors = []

    def generate_status():
        nonlocal success_count, failure_count, skipped_count
        yield "Processing started...\n"
        
        for row in reader:
            name = row.get("name", "").strip()
            email = row.get("email", "").strip()
            age_str = row.get("age", "").strip()
            
            error_msg = []
            if not name:
                error_msg.append("Name is empty")
            if not is_valid_email(email):
                error_msg.append("Invalid email format")
            
            try:
                age = int(age_str)
                if not (0 <= age <= 150):
                    error_msg.append("Age out of range")
            except ValueError:
                error_msg.append("Invalid age")
                
            if error_msg:
                failure_count += 1
                yield f"Row failed: {row} - {', '.join(error_msg)}\n"
            else:
                data_store[email] = {"name": name, "age": age}
                success_count += 1
                yield f"Row success: {name}\n"
        
        yield f"Final: Success={success_count}, Failure={failure_count}\n"

    return StreamingResponse(generate_status(), media_type="text/plain")
