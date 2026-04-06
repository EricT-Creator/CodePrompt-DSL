from typing import List, Dict, Any

class Pipeline:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.steps = []
    
    def filter(self, fn):
        self.steps.append(('filter', fn))
        return self
    
    def map(self, fn):
        self.steps.append(('map', fn))
        return self
    
    def sort(self, key=None):
        self.steps.append(('sort', key))
        return self
    
    def limit(self, n: int):
        self.steps.append(('limit', n))
        return self
    
    def execute(self) -> List[Dict[str, Any]]:
        result = self.data.copy()
        
        for step_type, func in self.steps:
            if step_type == 'filter':
                result = [item for item in result if func(item)]
            elif step_type == 'map':
                result = [func(item) for item in result]
            elif step_type == 'sort':
                result.sort(key=func)
            elif step_type == 'limit':
                result = result[:func]
        
        return result

if __name__ == "__main__":
    # 示例用法
    data = [
        {"name": "张三", "age": 30, "city": "北京"},
        {"name": "李四", "age": 25, "city": "上海"},
        {"name": "王五", "age": 35, "city": "广州"}
    ]
    
    pipeline = Pipeline(data).filter(lambda x: x["age"] > 25).map(lambda x: {"name": x["name"], "age": x["age"]}).sort(key=lambda x: x["age"]).limit(2)
    result = pipeline.execute()
    print(result)