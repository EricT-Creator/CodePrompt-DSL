from fastapi import FastAPI, Query
from typing import List, Dict

app = FastAPI()

# 模拟数据 - 50 条
mock_items = [
    {"id": i, "name": f"项目 {i}", "price": round(10 + (i * 2.5), 2)}
    for i in range(1, 51)
]

@app.get("/items")
async def get_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50)
):
    total = len(mock_items)
    total_pages = (total + page_size - 1) // page_size
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items_page = mock_items[start_idx:end_idx]
    
    return {
        "items": items_page,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)