"""
CSV批量导入API - 流式响应，逐行验证
不使用pandas，仅用csv标准库
"""

import csv
import io
import re
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="CSV Batch Import API")

# ===== 数据验证 =====

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def validate_row(row_num: int, row: dict) -> Optional[dict]:
    name = (row.get("name") or row.get("姓名") or "").strip()
    email = (row.get("email") or row.get("邮箱") or "").strip()
    age_str = (row.get("age") or row.get("年龄") or "").strip()

    errors = []

    if not name:
        errors.append("姓名不能为空")

    if not email:
        errors.append("邮箱不能为空")
    elif not EMAIL_PATTERN.match(email):
        errors.append("邮箱格式不正确")

    if not age_str:
        errors.append("年龄不能为空")
    else:
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                errors.append("年龄必须在0-150之间")
        except ValueError:
            errors.append("年龄必须是数字")

    if errors:
        return {"row": row_num, "status": "failed", "data": row, "errors": errors}
    return None

# ===== 内存存储 =====

records: list[dict] = []

# ===== 路由 =====

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="请上传CSV文件")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码不支持，请使用UTF-8或GBK")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV文件为空或格式不正确")

    total = 0
    success = 0
    failed = 0
    new_records = []

    def generate():
        nonlocal total, success, failed
        for row_num, row in enumerate(reader, start=2):
            total += 1
            error = validate_row(row_num, row)

            if error:
                failed += 1
                yield f'{{"row":{error["row"]},"status":"failed","errors":{error["errors"]}}}\n'
            else:
                success += 1
                record = {
                    "id": str(uuid.uuid4()),
                    "name": row.get("name") or row.get("姓名", "").strip(),
                    "email": row.get("email") or row.get("邮箱", "").strip(),
                    "age": int(row.get("age") or row.get("年龄", "0").strip()),
                }
                new_records.append(record)
                yield f'{{"row":{row_num},"status":"success","id":"{record["id"]}"}}\n'

        records.extend(new_records)
        summary = f'{{"total":{total},"success":{success},"failed":{failed}}}\n'
        yield summary

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": "attachment; filename=import_result.ndjson",
        },
    )

@app.get("/data")
async def get_data():
    return {
        "total": len(records),
        "records": records,
    }

# ===== 异常处理 =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
