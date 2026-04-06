from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import csv
import io
import re
from typing import List, Dict, Any
from dataclasses import dataclass

app = FastAPI()

storage: List[Dict[str, Any]] = []

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

def validate_name(name: str) -> ValidationResult:
    errors = []
    if not name or not name.strip():
        errors.append("姓名不能为空")
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

def validate_email(email: str) -> ValidationResult:
    errors = []
    if not email or not email.strip():
        errors.append("邮箱不能为空")
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        errors.append("邮箱格式不正确")
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

def validate_age(age_str: str) -> ValidationResult:
    errors = []
    if not age_str or not age_str.strip():
        errors.append("年龄不能为空")
    else:
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                errors.append("年龄必须在0-150之间")
        except ValueError:
            errors.append("年龄必须是数字")
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

def validate_row(row: Dict[str, str], row_num: int) -> ValidationResult:
    errors = []
    
    name_result = validate_name(row.get('name', ''))
    if not name_result.is_valid:
        errors.extend([f"第{row_num}行-姓名: {e}" for e in name_result.errors])
    
    email_result = validate_email(row.get('email', ''))
    if not email_result.is_valid:
        errors.extend([f"第{row_num}行-邮箱: {e}" for e in email_result.errors])
    
    age_result = validate_age(row.get('age', ''))
    if not age_result.is_valid:
        errors.extend([f"第{row_num}行-年龄: {e}" for e in age_result.errors])
    
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只接受CSV文件")
    
    async def generate():
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        total = 0
        success = 0
        failed = 0
        
        for row_num, row in enumerate(csv_reader, start=1):
            total += 1
            validation = validate_row(row, row_num)
            
            if validation.is_valid:
                record = {
                    'name': row['name'].strip(),
                    'email': row['email'].strip(),
                    'age': int(row['age'])
                }
                storage.append(record)
                success += 1
                yield f'{{"row": {row_num}, "status": "success", "data": {record}}}\n'
            else:
                failed += 1
                yield f'{{"row": {row_num}, "status": "error", "errors": {validation.errors}}}\n'
        
        summary = {
            "summary": True,
            "total": total,
            "success": success,
            "failed": failed
        }
        yield f'{{"summary": true, "total": {total}, "success": {success}, "failed": {failed}}}\n'
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.get("/data")
def get_data():
    return {"records": storage, "count": len(storage)}

@app.delete("/data")
def clear_data():
    storage.clear()
    return {"message": "数据已清空"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
