#!/usr/bin/env python3
"""
批量导入API - 使用FastAPI实现CSV文件导入
支持流式处理、验证和统计
"""

import csv
import io
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Generator
from dataclasses import dataclass, field
from enum import Enum

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator, ValidationError


# 数据模型
class ImportRecord(BaseModel):
    """导入记录"""
    name: str
    email: str
    age: int
    department: Optional[str] = None
    salary: Optional[float] = None
    hire_date: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('姓名不能为空')
        if len(v.strip()) > 100:
            raise ValueError('姓名长度不能超过100个字符')
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('邮箱不能为空')
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v.strip()):
            raise ValueError('无效的邮箱格式')
        
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0:
            raise ValueError('年龄不能为负数')
        if v > 150:
            raise ValueError('年龄不能超过150岁')
        return v
    
    @validator('salary')
    def validate_salary(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError('薪资不能为负数')
            if v > 10000000:  # 1000万
                raise ValueError('薪资不能超过10,000,000')
        return v
    
    @validator('hire_date')
    def validate_hire_date(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                try:
                    datetime.strptime(v, '%Y/%m/%d')
                except ValueError:
                    raise ValueError('入职日期格式应为 YYYY-MM-DD 或 YYYY/MM/DD')
        return v


class ImportResult(BaseModel):
    """导入结果"""
    line_number: int
    record: Optional[ImportRecord] = None
    status: str  # "success", "error", "warning"
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ImportSummary(BaseModel):
    """导入统计摘要"""
    filename: str
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    warning_records: int = 0
    processing_time_seconds: float = 0.0
    start_time: float
    end_time: float
    error_details: List[Dict[str, Any]] = field(default_factory=list)
    column_mapping: Optional[Dict[str, str]] = None


class DataQuery(BaseModel):
    """数据查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")
    department: Optional[str] = None
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    sort_by: Optional[str] = Field(None, description="排序字段: name, age, salary")
    sort_order: str = Field("asc", description="排序顺序: asc, desc")


# CSV解析和验证器
class CSVValidator:
    """CSV验证器"""
    
    def __init__(self):
        self.required_columns = {"name", "email", "age"}
        self.optional_columns = {"department", "salary", "hire_date"}
        self.all_columns = self.required_columns.union(self.optional_columns)
    
    def detect_columns(self, header_row: List[str]) -> Dict[str, str]:
        """检测CSV列名映射"""
        column_mapping = {}
        
        for csv_col in header_row:
            csv_col_lower = csv_col.strip().lower()
            
            # 尝试匹配标准列名
            matched = False
            for std_col in self.all_columns:
                if std_col in csv_col_lower or csv_col_lower in std_col:
                    column_mapping[std_col] = csv_col
                    matched = True
                    break
            
            # 如果没有匹配，尝试模糊匹配
            if not matched:
                if "name" in csv_col_lower or "姓名" in csv_col:
                    column_mapping["name"] = csv_col
                elif "email" in csv_col_lower or "邮箱" in csv_col or "mail" in csv_col_lower:
                    column_mapping["email"] = csv_col
                elif "age" in csv_col_lower or "年龄" in csv_col:
                    column_mapping["age"] = csv_col
                elif "department" in csv_col_lower or "部门" in csv_col or "dept" in csv_col_lower:
                    column_mapping["department"] = csv_col
                elif "salary" in csv_col_lower or "薪资" in csv_col or "工资" in csv_col:
                    column_mapping["salary"] = csv_col
                elif "hire" in csv_col_lower or "date" in csv_col_lower or "入职" in csv_col:
                    column_mapping["hire_date"] = csv_col
        
        return column_mapping
    
    def map_row(self, row: Dict[str, str], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """映射CSV行到标准字段"""
        mapped = {}
        
        for std_col, csv_col in column_mapping.items():
            if csv_col in row:
                value = row[csv_col].strip()
                mapped[std_col] = value if value else None
        
        return mapped
    
    def validate_row(self, row_data: Dict[str, Any], line_number: int) -> ImportResult:
        """验证单行数据"""
        try:
            # 检查必填字段
            missing_fields = []
            for field_name in self.required_columns:
                if field_name not in row_data or not row_data[field_name]:
                    missing_fields.append(field_name)
            
            if missing_fields:
                return ImportResult(
                    line_number=line_number,
                    status="error",
                    error_message=f"缺少必填字段: {', '.join(missing_fields)}"
                )
            
            # 尝试转换为ImportRecord
            try:
                # 转换数据类型
                converted_data = {}
                for key, value in row_data.items():
                    if value is None:
                        converted_data[key] = None
                    elif key == "age":
                        try:
                            converted_data[key] = int(value)
                        except ValueError:
                            return ImportResult(
                                line_number=line_number,
                                status="error",
                                error_message=f"年龄必须是整数: {value}"
                            )
                    elif key == "salary":
                        try:
                            converted_data[key] = float(value)
                        except ValueError:
                            return ImportResult(
                                line_number=line_number,
                                status="error", 
                                error_message=f"薪资必须是数字: {value}"
                            )
                    else:
                        converted_data[key] = value
                
                # 创建ImportRecord
                record = ImportRecord(**converted_data)
                
                # 检查警告
                warnings = []
                if record.salary is None:
                    warnings.append("薪资字段为空")
                if record.department is None:
                    warnings.append("部门字段为空")
                if record.hire_date is None:
                    warnings.append("入职日期字段为空")
                
                status = "warning" if warnings else "success"
                
                return ImportResult(
                    line_number=line_number,
                    record=record,
                    status=status,
                    warnings=warnings
                )
                
            except ValidationError as e:
                errors = []
                for error in e.errors():
                    field_name = " -> ".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    errors.append(f"{field_name}: {msg}")
                
                return ImportResult(
                    line_number=line_number,
                    status="error",
                    error_message=f"验证错误: {', '.join(errors)}"
                )
                
        except Exception as e:
            return ImportResult(
                line_number=line_number,
                status="error",
                error_message=f"处理错误: {str(e)}"
            )


# 数据存储
class DataStore:
    """数据存储管理器"""
    
    def __init__(self):
        self.records: List[ImportRecord] = []
        self.import_history: List[ImportSummary] = []
        self.last_import_id: int = 0
    
    def add_records(self, records: List[ImportRecord]) -> None:
        """添加记录到存储"""
        self.records.extend(records)
    
    def get_records(self, query: DataQuery) -> Tuple[List[ImportRecord], int]:
        """获取记录（带分页和过滤）"""
        filtered = self.records.copy()
        
        # 应用过滤器
        if query.department:
            filtered = [r for r in filtered if r.department and query.department.lower() in r.department.lower()]
        
        if query.min_age is not None:
            filtered = [r for r in filtered if r.age >= query.min_age]
        
        if query.max_age is not None:
            filtered = [r for r in filtered if r.age <= query.max_age]
        
        # 应用排序
        if query.sort_by:
            reverse = query.sort_order.lower() == "desc"
            
            if query.sort_by == "name":
                filtered.sort(key=lambda x: x.name, reverse=reverse)
            elif query.sort_by == "age":
                filtered.sort(key=lambda x: x.age, reverse=reverse)
            elif query.sort_by == "salary":
                filtered.sort(key=lambda x: x.salary if x.salary is not None else float('-inf'), reverse=reverse)
        
        # 分页
        total = len(filtered)
        start_idx = (query.page - 1) * query.page_size
        end_idx = start_idx + query.page_size
        
        paginated = filtered[start_idx:end_idx]
        
        return paginated, total
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据统计"""
        if not self.records:
            return {
                "total_records": 0,
                "departments": [],
                "age_stats": {},
                "salary_stats": {}
            }
        
        # 部门统计
        departments = {}
        for record in self.records:
            if record.department:
                dept = record.department
                departments[dept] = departments.get(dept, 0) + 1
        
        # 年龄统计
        ages = [r.age for r in self.records]
        
        # 薪资统计（仅统计有薪资的记录）
        salaries = [r.salary for r in self.records if r.salary is not None]
        
        return {
            "total_records": len(self.records),
            "departments": [
                {"name": dept, "count": count}
                for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True)
            ],
            "age_stats": {
                "min": min(ages) if ages else 0,
                "max": max(ages) if ages else 0,
                "average": sum(ages) / len(ages) if ages else 0,
                "median": sorted(ages)[len(ages) // 2] if ages else 0
            },
            "salary_stats": {
                "min": min(salaries) if salaries else 0,
                "max": max(salaries) if salaries else 0,
                "average": sum(salaries) / len(salaries) if salaries else 0,
                "median": sorted(salaries)[len(salaries) // 2] if salaries else 0,
                "records_with_salary": len(salaries)
            } if salaries else {
                "records_with_salary": 0
            }
        }
    
    def add_import_summary(self, summary: ImportSummary) -> None:
        """添加入口历史"""
        self.import_history.append(summary)
    
    def get_import_history(self, limit: int = 10) -> List[ImportSummary]:
        """获取导入历史"""
        return self.import_history[-limit:] if self.import_history else []
    
    def clear_all(self) -> None:
        """清除所有数据"""
        self.records.clear()
        self.import_history.clear()


# CSV流式处理器
async def process_csv_stream(
    file: UploadFile,
    validator: CSVValidator
) -> Generator[Dict[str, Any], None, None]:
    """流式处理CSV文件"""
    try:
        # 读取文件内容
        content = await file.read()
        
        # 使用StringIO创建文本流
        text_stream = io.StringIO(content.decode('utf-8-sig'))
        
        # 创建CSV读取器
        csv_reader = csv.DictReader(text_stream)
        
        # 检测列映射
        if csv_reader.fieldnames:
            column_mapping = validator.detect_columns(csv_reader.fieldnames)
            
            # 检查必填字段
            missing_required = []
            for req_col in validator.required_columns:
                if req_col not in column_mapping:
                    missing_required.append(req_col)
            
            if missing_required:
                yield {
                    "type": "error",
                    "message": f"CSV文件缺少必填列: {', '.join(missing_required)}",
                    "column_mapping": column_mapping
                }
                return
            
            yield {
                "type": "header_info",
                "column_mapping": column_mapping,
                "original_headers": csv_reader.fieldnames
            }
        else:
            yield {
                "type": "error",
                "message": "CSV文件没有表头或为空"
            }
            return
        
        # 处理每一行
        line_number = 1  # 表头算第1行
        records_processed = 0
        
        for row in csv_reader:
            line_number += 1
            records_processed += 1
            
            # 映射行数据
            mapped_row = validator.map_row(row, column_mapping)
            
            # 验证行数据
            result = validator.validate_row(mapped_row, line_number)
            
            yield {
                "type": "record_result",
                "line_number": line_number,
                "result": result.dict(),
                "records_processed": records_processed
            }
            
            # 每100行输出一次进度
            if records_processed % 100 == 0:
                yield {
                    "type": "progress",
                    "records_processed": records_processed,
                    "line_number": line_number
                }
        
        yield {
            "type": "complete",
            "total_records": records_processed,
            "total_lines": line_number
        }
        
    except UnicodeDecodeError:
        yield {
            "type": "error",
            "message": "文件编码错误，请使用UTF-8编码的CSV文件"
        }
    except Exception as e:
        yield {
            "type": "error",
            "message": f"处理CSV文件时发生错误: {str(e)}"
        }


# 创建应用
app = FastAPI(
    title="批量导入API",
    description="CSV文件批量导入和数据处理服务",
    version="1.0.0"
)

# 全局实例
validator = CSVValidator()
data_store = DataStore()


# API路由
@app.get("/")
async def root():
    """根路由，返回API信息"""
    return {
        "name": "批量导入API",
        "version": "1.0.0",
        "description": "CSV文件批量导入、验证和数据处理服务",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "API信息"},
            {"path": "/import", "method": "POST", "description": "导入CSV文件"},
            {"path": "/data", "method": "GET", "description": "查询导入的数据"},
            {"path": "/stats", "method": "GET", "description": "获取数据统计"},
            {"path": "/import/history", "method": "GET", "description": "获取导入历史"},
            {"path": "/health", "method": "GET", "description": "健康检查"}
        ],
        "data_model": {
            "required_fields": ["name", "email", "age"],
            "optional_fields": ["department", "salary", "hire_date"],
            "validation_rules": {
                "name": "非空，长度≤100字符",
                "email": "有效的邮箱格式",
                "age": "0-150之间的整数",
                "salary": "正数，≤10,000,000",
                "hire_date": "YYYY-MM-DD或YYYY/MM/DD格式"
            }
        }
    }


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    """导入CSV文件"""
    start_time = time.time()
    
    # 检查文件类型
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="只支持CSV文件"
        )
    
    # 收集结果
    results = []
    successful_records = []
    failed_records = []
    warning_records = []
    column_mapping = None
    
    async def process_stream():
        nonlocal column_mapping
        
        async for chunk in file.stream():
            # 这里简化处理，实际应该使用真正的流式处理
            pass
    
    # 流式处理CSV
    async def generate():
        nonlocal column_mapping, successful_records, failed_records, warning_records
        
        async for event in process_csv_stream(file, validator):
            if event["type"] == "header_info":
                column_mapping = event["column_mapping"]
                yield f"data: {json.dumps(event)}\n\n"
            
            elif event["type"] == "record_result":
                result_data = event["result"]
                result = ImportResult(**result_data)
                results.append(result)
                
                if result.status == "success":
                    successful_records.append(result.record)
                elif result.status == "error":
                    failed_records.append(result)
                elif result.status == "warning":
                    warning_records.append(result)
                    successful_records.append(result.record)  # 警告记录也算成功
                
                yield f"data: {json.dumps(event)}\n\n"
            
            elif event["type"] == "progress":
                yield f"data: {json.dumps(event)}\n\n"
            
            elif event["type"] == "complete":
                # 处理完成，保存数据
                if successful_records:
                    data_store.add_records(successful_records)
                
                # 创建导入摘要
                end_time = time.time()
                summary = ImportSummary(
                    filename=file.filename,
                    total_records=len(results),
                    successful_records=len(successful_records),
                    failed_records=len(failed_records),
                    warning_records=len(warning_records),
                    processing_time_seconds=end_time - start_time,
                    start_time=start_time,
                    end_time=end_time,
                    error_details=[
                        {
                            "line_number": r.line_number,
                            "error_message": r.error_message
                        }
                        for r in failed_records
                    ],
                    column_mapping=column_mapping
                )
                
                data_store.add_import_summary(summary)
                
                # 发送完成事件
                complete_event = {
                    "type": "complete",
                    "summary": summary.dict(),
                    "successful_count": len(successful_records),
                    "failed_count": len(failed_records),
                    "warning_count": len(warning_records)
                }
                yield f"data: {json.dumps(complete_event)}\n\n"
            
            elif event["type"] == "error":
                yield f"data: {json.dumps(event)}\n\n"
                return
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )


@app.post("/import/sync")
async def import_csv_sync(file: UploadFile = File(...)):
    """同步导入CSV文件（返回完整结果）"""
    start_time = time.time()
    
    # 检查文件类型
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="只支持CSV文件"
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        text_stream = io.StringIO(content.decode('utf-8-sig'))
        
        # 解析CSV
        csv_reader = csv.DictReader(text_stream)
        
        if not csv_reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV文件没有表头或为空")
        
        # 检测列映射
        column_mapping = validator.detect_columns(csv_reader.fieldnames)
        
        # 检查必填字段
        missing_required = []
        for req_col in validator.required_columns:
            if req_col not in column_mapping:
                missing_required.append(req_col)
        
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"CSV文件缺少必填列: {', '.join(missing_required)}"
            )
        
        # 处理每一行
        results = []
        successful_records = []
        failed_records = []
        warning_records = []
        
        line_number = 1
        for row in csv_reader:
            line_number += 1
            
            # 映射行数据
            mapped_row = validator.map_row(row, column_mapping)
            
            # 验证行数据
            result = validator.validate_row(mapped_row, line_number)
            results.append(result)
            
            if result.status == "success":
                successful_records.append(result.record)
            elif result.status == "error":
                failed_records.append(result)
            elif result.status == "warning":
                warning_records.append(result)
                successful_records.append(result.record)
        
        # 保存成功记录
        if successful_records:
            data_store.add_records(successful_records)
        
        # 创建导入摘要
        end_time = time.time()
        summary = ImportSummary(
            filename=file.filename,
            total_records=len(results),
            successful_records=len(successful_records),
            failed_records=len(failed_records),
            warning_records=len(warning_records),
            processing_time_seconds=end_time - start_time,
            start_time=start_time,
            end_time=end_time,
            error_details=[
                {
                    "line_number": r.line_number,
                    "error_message": r.error_message
                }
                for r in failed_records
            ],
            column_mapping=column_mapping
        )
        
        data_store.add_import_summary(summary)
        
        return {
            "success": True,
            "summary": summary.dict(),
            "results_preview": [
                r.dict() for r in results[:10]  # 只返回前10条结果预览
            ],
            "total_results": len(results),
            "column_mapping": column_mapping
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用UTF-8编码的CSV文件")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理CSV文件时发生错误: {str(e)}")


@app.get("/data")
async def get_data(query: DataQuery = Depends()):
    """查询导入的数据"""
    records, total = data_store.get_records(query)
    
    return {
        "success": True,
        "data": [record.dict() for record in records],
        "pagination": {
            "page": query.page,
            "page_size": query.page_size,
            "total_records": total,
            "total_pages": (total + query.page_size - 1) // query.page_size
        },
        "query": query.dict(),
        "timestamp": time.time()
    }


@app.get("/stats")
async def get_stats():
    """获取数据统计"""
    stats = data_store.get_stats()
    
    return {
        "success": True,
        "stats": stats,
        "timestamp": time.time()
    }


@app.get("/import/history")
async def get_import_history(limit: int = Query(10, ge=1, le=100)):
    """获取导入历史"""
    history = data_store.get_import_history(limit)
    
    return {
        "success": True,
        "history": [summary.dict() for summary in history],
        "total_imports": len(data_store.import_history),
        "limit": limit,
        "timestamp": time.time()
    }


@app.delete("/data")
async def clear_all_data(confirm: bool = Query(False, description="确认删除所有数据")):
    """清除所有数据"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="需要确认参数 confirm=true 来删除所有数据"
        )
    
    data_store.clear_all()
    
    return {
        "success": True,
        "message": "所有数据已清除",
        "timestamp": time.time()
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "batch_import_api",
        "timestamp": time.time(),
        "data_stats": data_store.get_stats()
    }


# 模板下载
@app.get("/template")
async def download_template():
    """下载CSV模板文件"""
    template_content = """name,email,age,department,salary,hire_date
张三,zhangsan@example.com,30,技术部,50000,2020-01-15
李四,lisi@example.com,25,市场部,45000,2021-03-20
王五,wangwu@example.com,35,财务部,60000,2019-07-10
赵六,zhaoliu@example.com,28,人力资源部,48000,2022-05-05

说明：
1. name: 姓名（必填），长度不超过100字符
2. email: 邮箱（必填），有效的邮箱格式
3. age: 年龄（必填），0-150之间的整数
4. department: 部门（可选）
5. salary: 薪资（可选），正数
6. hire_date: 入职日期（可选），YYYY-MM-DD或YYYY/MM/DD格式"""
    
    return StreamingResponse(
        io.StringIO(template_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=import_template.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


# 运行应用
if __name__ == "__main__":
    import uvicorn
    import json
    
    print("启动批量导入API服务...")
    print(f"访问地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print("\n主要功能:")
    print("1. CSV文件批量导入（支持流式处理）")
    print("2. 数据验证（姓名、邮箱、年龄等）")
    print("3. 数据查询和分页")
    print("4. 数据统计和分析")
    print("\n使用示例:")
    print("- POST /import - 上传CSV文件（推荐使用流式端点）")
    print("- GET /template - 下载CSV模板文件")
    print("- GET /data?page=1&page_size=20 - 查询导入的数据")
    print("- GET /stats - 查看数据统计")
    print("- GET /import/history - 查看导入历史")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)