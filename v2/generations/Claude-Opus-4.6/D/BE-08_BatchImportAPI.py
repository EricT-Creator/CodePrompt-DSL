import csv
import io
import re
from typing import Generator

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse

app = FastAPI()

db: dict[int, dict] = {}
_next_id: int = 1

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _validate_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    name = row.get("name", "").strip()
    if not name:
        errors.append("姓名不能为空")
    email = row.get("email", "").strip()
    if not EMAIL_RE.match(email):
        errors.append(f"邮箱格式无效: {email!r}")
    age_str = row.get("age", "").strip()
    try:
        age = int(age_str)
        if age < 0 or age > 150:
            errors.append(f"年龄超出范围(0-150): {age}")
    except ValueError:
        errors.append(f"年龄非整数: {age_str!r}")
    return errors


def _process_csv(content: str) -> Generator[str, None, None]:
    global _next_id
    reader = csv.DictReader(io.StringIO(content))
    success = 0
    failed = 0
    skipped = 0
    error_details: list[str] = []

    for line_no, row in enumerate(reader, start=2):
        if all(v.strip() == "" for v in row.values()):
            skipped += 1
            yield f"行{line_no}: 跳过(空行)\n"
            continue
        errs = _validate_row(row)
        if errs:
            failed += 1
            detail = f"行{line_no}: 失败 - {'; '.join(errs)}"
            error_details.append(detail)
            yield detail + "\n"
            continue
        record = {
            "id": _next_id,
            "name": row["name"].strip(),
            "email": row["email"].strip(),
            "age": int(row["age"].strip()),
        }
        db[_next_id] = record
        _next_id += 1
        success += 1
        yield f"行{line_no}: 成功 - {record['name']}\n"

    yield "---\n"
    yield f"处理完毕: 成功={success}, 失败={failed}, 跳过={skipped}\n"
    if error_details:
        yield "错误详情:\n"
        for d in error_details:
            yield f"  {d}\n"


@app.post("/import")
async def batch_import(file: UploadFile = File(...)):
    raw = await file.read()
    content = raw.decode("utf-8")

    def stream():
        yield from _process_csv(content)

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")
