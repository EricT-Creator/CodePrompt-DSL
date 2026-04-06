from typing import Dict, List, Set, Optional, Callable, Any
from collections import deque


class CycleError(Exception):
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


class DAGScheduler:
    def __init__(self):
        self.tasks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}

    def add_task(self, name: str, func: Callable) -> None:
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        self.tasks[name] = func
        self.dependencies.setdefault(name, set())
        self.dependents.setdefault(name, set())

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if depends_on not in self.tasks:
            raise ValueError(f"Dependency task '{depends_on}' does not exist")
        if task == depends_on:
            raise ValueError(f"Task cannot depend on itself: '{task}'")
        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)

    def validate(self) -> bool:
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.dependencies.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    cycle_start = path.index(dep)
                    raise CycleError(path[cycle_start:] + [dep])

            path.pop()
            rec_stack.remove(node)
            return False

        for task in self.tasks:
            if task not in visited:
                if dfs(task):
                    return False
        return True

    def get_execution_order(self) -> List[str]:
        self.validate()
        in_degree: Dict[str, int] = {t: 0 for t in self.tasks}
        for task, deps in self.dependencies.items():
            in_degree[task] = len(deps)

        queue = deque(sorted(t for t, d in in_degree.items() if d == 0))
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in sorted(self.dependents.get(node, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self.tasks):
            remaining = [t for t in self.tasks if t not in set(order)]
            raise CycleError(remaining)

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        self.validate()
        completed: Set[str] = set()
        groups: List[Set[str]] = []
        remaining = set(self.tasks.keys())

        while remaining:
            group: Set[str] = set()
            for task in sorted(remaining):
                if self.dependencies.get(task, set()).issubset(completed):
                    group.add(task)

            if not group:
                unresolved = remaining - set(completed)
                raise CycleError(list(unresolved))

            groups.append(group)
            completed.update(group)
            remaining -= group

        return groups

    def execute(self) -> Dict[str, Any]:
        order = self.get_execution_order()
        results: Dict[str, Any] = {}

        for task_name in order:
            func = self.tasks[task_name]
            try:
                result = func(**results)
                results[task_name] = result
            except TypeError:
                result = func()
                results[task_name] = result

        return results


def demo():
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: {"raw": [1, 2, 3, 4, 5]})
    scheduler.add_task("clean_data", lambda raw: {"cleaned": [x * 2 for x in raw]})
    scheduler.add_task("split_data", lambda cleaned: {"train": cleaned[:3], "test": cleaned[3:]})
    scheduler.add_task("train_model", lambda train: {"model": f"trained_on_{len(train)}_items"})
    scheduler.add_task("evaluate", lambda model, test: {"score": len(test) * 0.8})
    scheduler.add_task("report", lambda score, model: {"final": score, "model_name": model})

    scheduler.add_dependency("clean_data", "fetch_data")
    scheduler.add_dependency("split_data", "clean_data")
    scheduler.add_dependency("train_model", "split_data")
    scheduler.add_dependency("evaluate", "train_model")
    scheduler.add_dependency("evaluate", "split_data")
    scheduler.add_dependency("report", "evaluate")
    scheduler.add_dependency("report", "train_model")

    print("=== Validation ===")
    try:
        scheduler.validate()
        print("No cycles detected. DAG is valid.")
    except CycleError as e:
        print(f"Validation failed: {e}")
        return

    print("\n=== Execution Order (Topological Sort) ===")
    order = scheduler.get_execution_order()
    for i, task in enumerate(order, 1):
        print(f"  {i}. {task}")

    print("\n=== Parallel Groups ===")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups, 1):
        print(f"  Group {i}: {', '.join(sorted(group))}")

    print("\n=== Execution Results ===")
    results = scheduler.execute()
    for task, result in results.items():
        print(f"  {task}: {result}")


if __name__ == "__main__":
    demo()
