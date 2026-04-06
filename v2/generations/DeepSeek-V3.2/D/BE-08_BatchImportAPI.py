import csv
import io
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Generator, Optional
from enum import Enum

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, validator, ValidationError
import uvicorn

# 验证错误枚举
class ValidationErrorType(Enum):
    EMPTY_NAME = "姓名不能为空"
    INVALID_EMAIL = "邮箱格式不正确"
    INVALID_AGE = "年龄必须在0-150之间"
    MISSING_FIELD = "缺少必填字段"

# 数据模型
class PersonRecord(BaseModel):
    """个人记录数据模型"""
    name: str
    email: str
    age: int
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError(ValidationErrorType.EMPTY_NAME.value)
        return v.strip()
    
    @validator('email')
    def email_valid(cls, v):
        if not v:
            raise ValueError(ValidationErrorType.MISSING_FIELD.value)
        
        # 简单的邮箱验证正则
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError(ValidationErrorType.INVALID_EMAIL.value)
        
        return v
    
    @validator('age')
    def age_valid(cls, v):
        if v is None:
            raise ValueError(ValidationErrorType.MISSING_FIELD.value)
        
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError(ValidationErrorType.INVALID_AGE.value)
        
        if v < 0 or v > 150:
            raise ValueError(ValidationErrorType.INVALID_AGE.value)
        
        return v

# 处理结果模型
class ProcessResult(BaseModel):
    """单条记录处理结果"""
    row_number: int
    status: str  # "success" 或 "failed"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

class ImportSummary(BaseModel):
    """导入汇总"""
    total_records: int
    successful_records: int
    failed_records: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float

# 内存数据存储（生产环境应使用数据库）
data_store: List[Dict[str, Any]] = []

# CSV解析器
class CSVBatchImporter:
    def __init__(self):
        self.email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def validate_record(self, row: Dict[str, str], row_number: int) -> List[str]:
        """验证单条记录"""
        errors = []
        
        # 姓名验证
        name = row.get('name', '').strip()
        if not name:
            errors.append(ValidationErrorType.EMPTY_NAME.value)
        
        # 邮箱验证
        email = row.get('email', '').strip()
        if not email:
            errors.append(ValidationErrorType.MISSING_FIELD.value)
        elif not re.match(self.email_regex, email):
            errors.append(ValidationErrorType.INVALID_EMAIL.value)
        
        # 年龄验证
        age_str = row.get('age', '').strip()
        if not age_str:
            errors.append(ValidationErrorType.MISSING_FIELD.value)
        else:
            try:
                age = int(age_str)
                if age < 0 or age > 150:
                    errors.append(ValidationErrorType.INVALID_AGE.value)
            except ValueError:
                errors.append(ValidationErrorType.INVALID_AGE.value)
        
        return errors
    
    def parse_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """解析单条记录"""
        try:
            # 转换年龄为整数
            age_str = row.get('age', '').strip()
            age = int(age_str) if age_str else None
            
            record = {
                'name': row.get('name', '').strip(),
                'email': row.get('email', '').strip(),
                'age': age
            }
            
            # 使用Pydantic验证
            PersonRecord(**record)
            return record
            
        except (ValueError, ValidationError) as e:
            return None
    
    def stream_csv_processing(
        self, 
        file_content: bytes, 
        delimiter: str = ','
    ) -> Generator[ProcessResult, None, None]:
        """流式处理CSV文件"""
        # 将字节转换为文本流
        text_stream = io.StringIO(file_content.decode('utf-8'))
        
        # 创建CSV读取器
        csv_reader = csv.DictReader(text_stream, delimiter=delimiter)
        
        for row_number, row in enumerate(csv_reader, start=1):
            errors = self.validate_record(row, row_number)
            
            if errors:
                yield ProcessResult(
                    row_number=row_number,
                    status="failed",
                    error="; ".join(errors),
                    error_type="validation"
                )
            else:
                record = self.parse_record(row)
                if record:
                    data_store.append(record)
                    
                    yield ProcessResult(
                        row_number=row_number,
                        status="success",
                        data=record
                    )
                else:
                    yield ProcessResult(
                        row_number=row_number,
                        status="failed",
                        error="解析失败",
                        error_type="parsing"
                    )

# FastAPI应用
app = FastAPI(
    title="CSV批量导入API",
    description="支持CSV文件批量导入、流式验证和处理的API服务",
    version="1.0.0"
)

# 导入器实例
importer = CSVBatchImporter()

# 请求响应模型
class ImportResponse(BaseModel):
    summary: ImportSummary
    results: List[ProcessResult]

class DataResponse(BaseModel):
    records: List[Dict[str, Any]]
    count: int
    page: int = 1
    total_pages: int = 1

# API端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "CSV批量导入API",
        "endpoints": {
            "POST /import": "上传CSV文件进行批量导入",
            "GET /data": "查看所有导入的数据",
            "GET /data/{page}": "分页查看数据",
            "GET /stats": "查看导入统计信息",
            "DELETE /data": "清除所有数据（需管理员权限）"
        },
        "supported_fields": ["name", "email", "age"],
        "validation_rules": {
            "name": "非空字符串",
            "email": "有效的邮箱格式",
            "age": "0-150之间的整数"
        },
        "current_record_count": len(data_store)
    }

@app.post("/import", response_model=ImportResponse)
async def import_csv(
    file: UploadFile = File(..., description="CSV文件上传"),
    delimiter: str = ','
):
    """
    批量导入CSV文件
    
    Args:
        file: CSV文件
        delimiter: CSV分隔符，默认为逗号
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="仅支持CSV文件"
        )
    
    start_time = datetime.now()
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 处理CSV并生成流式响应
        results = []
        process_stream = importer.stream_csv_processing(file_content, delimiter)
        
        for result in process_stream:
            results.append(result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        successful = sum(1 for r in results if r.status == "success")
        failed = len(results) - successful
        
        summary = ImportSummary(
            total_records=len(results),
            successful_records=successful,
            failed_records=failed,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
        
        return ImportResponse(
            summary=summary,
            results=results
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理文件时发生错误: {str(e)}"
        )

@app.get("/import/stream")
async def stream_import(
    file: UploadFile = File(..., description="CSV文件上传"),
    delimiter: str = ','
):
    """
    流式导入CSV文件（实时返回处理结果）
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="仅支持CSV文件"
        )
    
    async def event_generator():
        """生成服务器发送事件"""
        try:
            file_content = await file.read()
            
            yield f"data: {json.dumps({'type': 'start', 'message': '开始处理CSV文件'})}\n\n"
            
            process_stream = importer.stream_csv_processing(file_content, delimiter)
            for result in process_stream:
                yield f"data: {json.dumps({
                    'type': 'progress',
                    'row_number': result.row_number,
                    'status': result.status,
                    'data': result.data,
                    'error': result.error
                })}\n\n"
            
            successful = sum(1 for r in process_stream if r.status == "success")
            failed = len(data_store) - successful
            
            yield f"data: {json.dumps({
                'type': 'complete',
                'message': '处理完成',
                'summary': {
                    'total': len(data_store),
                    'successful': successful,
                    'failed': failed
                }
            })}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/data", response_model=DataResponse)
async def get_all_data(page: int = 1, page_size: int = 50):
    """获取所有导入的数据"""
    if page < 1:
        page = 1
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    total_records = len(data_store)
    total_pages = (total_records + page_size - 1) // page_size
    
    records = data_store[start_idx:end_idx]
    
    return DataResponse(
        records=records,
        count=len(records),
        page=page,
        total_pages=total_pages
    )

@app.get("/data/{record_id}")
async def get_record_by_id(record_id: int):
    """根据ID获取单条记录"""
    if record_id < 1 or record_id > len(data_store):
        raise HTTPException(
            status_code=404,
            detail=f"记录ID {record_id} 不存在"
        )
    
    record = data_store[record_id - 1]  # ID从1开始
    return {
        "id": record_id,
        **record
    }

@app.get("/stats")
async def get_import_stats():
    """获取导入统计信息"""
    total_records = len(data_store)
    
    if total_records == 0:
        return {
            "total_records": 0,
            "message": "暂无数据"
        }
    
    # 计算年龄分布
    age_distribution = {}
    for record in data_store:
        age = record.get('age')
        if age is not None:
            age_group = f"{age // 10 * 10}-{age // 10 * 10 + 9}"
            age_distribution[age_group] = age_distribution.get(age_group, 0) + 1
    
    # 计算邮箱域名分布
    email_domains = {}
    for record in data_store:
        email = record.get('email', '')
        if '@' in email:
            domain = email.split('@')[1]
            email_domains[domain] = email_domains.get(domain, 0) + 1
    
    # 按姓名长度分组
    name_lengths = {}
    for record in data_store:
        name = record.get('name', '')
        length = len(name)
        length_group = f"{length}字符"
        name_lengths[length_group] = name_lengths.get(length_group, 0) + 1
    
    return {
        "total_records": total_records,
        "age_distribution": age_distribution,
        "email_domains": dict(sorted(email_domains.items(), key=lambda x: x[1], reverse=True)[:10]),
        "name_lengths": name_lengths,
        "data_samples": data_store[:5] if total_records > 5 else data_store,
        "last_updated": datetime.now().isoformat()
    }

@app.delete("/data")
async def clear_all_data(request: Request):
    """清除所有数据（需管理员权限）"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 简单的管理员检查（生产环境应使用更安全的认证）
    if client_ip != "127.0.0.1":
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以清除数据"
        )
    
    records_count = len(data_store)
    data_store.clear()
    
    return {
        "status": "success",
        "message": f"已清除 {records_count} 条记录",
        "remaining_records": 0
    }

@app.get("/validate/sample")
async def validate_sample_record():
    """验证示例记录"""
    sample_records = [
        {
            "name": "张三",
            "email": "zhangsan@example.com",
            "age": 30
        },
        {
            "name": "",
            "email": "invalid-email",
            "age": 200
        }
    ]
    
    results = []
    
    for i, record in enumerate(sample_records, start=1):
        try:
            PersonRecord(**record)
            results.append({
                "record": record,
                "status": "valid",
                "message": "验证通过"
            })
        except ValidationError as e:
            results.append({
                "record": record,
                "status": "invalid",
                "errors": [err['msg'] for err in e.errors()]
            })
    
    return {
        "samples": results,
        "message": "验证规则演示"
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_store_size": len(data_store),
        "memory_usage_mb": "N/A"  # 生产环境可添加实际内存使用
    }

# 错误处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Pydantic验证错误处理器"""
    errors = [{"field": err["loc"][0], "message": err["msg"]} for err in exc.errors()]
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "errors": errors,
            "message": "数据验证失败"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("CSV批量导入API已启动")
    print(f"当前数据存储大小: {len(data_store)} 条记录")
    print("可用端点:")
    print("  POST /import     - 上传CSV文件进行批量导入")
    print("  GET  /data       - 查看所有导入的数据")
    print("  GET  /stats      - 查看导入统计信息")
    print("  GET  /health     - 健康检查")

if __name__ == "__main__":
    uvicorn.run(
        "BE_08_BatchImportAPI:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )