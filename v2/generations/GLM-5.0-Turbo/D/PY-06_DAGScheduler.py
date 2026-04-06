"""
DAG任务调度器 - 拓扑排序与并行分组
不使用networkx/graphlib，手动实现
"""


class CycleError(Exception):
    pass


class Task:
    def __init__(self, name: str, func=None):
        self.name = name
        self.func = func
        self.dependencies: set[str] = set()
        self.dependents: set[str] = set()

    def __repr__(self):
        return f"Task({self.name})"


class DAGScheduler:
    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def add_task(self, name: str, func=None):
        if name in self.tasks:
            raise ValueError(f"任务 '{name}' 已存在")
        self.tasks[name] = Task(name, func)

    def add_dependency(self, task_name: str, depends_on: str):
        if task_name not in self.tasks:
            raise ValueError(f"任务 '{task_name}' 不存在")
        if depends_on not in self.tasks:
            raise ValueError(f"依赖任务 '{depends_on}' 不存在")
        if task_name == depends_on:
            raise ValueError(f"任务不能依赖自身")

        self.tasks[task_name].dependencies.add(depends_on)
        self.tasks[depends_on].dependents.add(task_name)

    def validate(self):
        visited = set()
        rec_stack = set()

        def _dfs(name: str):
            visited.add(name)
            rec_stack.add(name)
            for dep in self.tasks[name].dependencies:
                if dep not in visited:
                    if _dfs(dep):
                        return True
                elif dep in rec_stack:
                    raise CycleError(f"检测到环依赖: {dep} -> {name}")
            rec_stack.discard(name)
            return False

        for name in self.tasks:
            if name not in visited:
                _dfs(name)

    def get_execution_order(self) -> list[str]:
        self.validate()

        in_degree = {name: len(task.dependencies) for name, task in self.tasks.items()}
        queue = [name for name, degree in in_degree.items() if degree == 0]
        queue.sort()
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in sorted(self.tasks[node].dependents):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
            queue.sort()

        if len(result) != len(self.tasks):
            raise CycleError("存在环依赖，无法完成拓扑排序")

        return result

    def get_parallel_groups(self) -> list[list[str]]:
        self.validate()

        completed = set()
        groups = []

        while len(completed) < len(self.tasks):
            ready = []
            for name, task in self.tasks.items():
                if name in completed:
                    continue
                if task.dependencies.issubset(completed):
                    ready.append(name)

            if not ready:
                raise CycleError("存在环依赖，无法分组")

            ready.sort()
            groups.append(ready)
            completed.update(ready)

        return groups

    def execute(self) -> dict:
        self.validate()
        order = self.get_execution_order()
        results = {}

        print(f"执行顺序: {' -> '.join(order)}")
        print()

        for name in order:
            task = self.tasks[name]
            deps = sorted(task.dependencies)
            if deps:
                print(f"执行 {name} (依赖: {', '.join(deps)})...")
            else:
                print(f"执行 {name}...")

            if task.func:
                result = task.func(**{dep: results.get(dep) for dep in task.dependencies})
                results[name] = result
                print(f"  结果: {result}")
            else:
                results[name] = None
                print(f"  完成 (无函数)")

        return results


def main():
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", func=lambda: "raw_data")
    scheduler.add_task("clean_data", func=lambda raw_data: f"cleaned_{raw_data}")
    scheduler.add_task("validate_data", func=lambda raw_data: f"validated_{raw_data}")
    scheduler.add_task("transform", func=lambda raw_data, validated: f"transformed_{validated}")
    scheduler.add_task("aggregate", func=lambda cleaned, transformed: f"agg_{cleaned}_+_{transformed}")
    scheduler.add_task("report", func=lambda agg: f"report_{agg}")

    scheduler.add_dependency("clean_data", "fetch_data")
    scheduler.add_dependency("validate_data", "fetch_data")
    scheduler.add_dependency("transform", "validate_data")
    scheduler.add_dependency("aggregate", "clean_data")
    scheduler.add_dependency("aggregate", "transform")
    scheduler.add_dependency("report", "aggregate")

    scheduler.validate()

    order = scheduler.get_execution_order()
    print(f"拓扑排序: {order}")

    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups):
        print(f"  第{i + 1}组 (可并行): {group}")

    print()
    results = scheduler.execute()
    print(f"\n全部任务结果: {results}")
    return results


if __name__ == "__main__":
    main()
