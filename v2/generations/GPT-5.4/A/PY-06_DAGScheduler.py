from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Set


class CycleError(Exception):
    pass


class DAGScheduler:
    def __init__(self) -> None:
        self.tasks: Dict[str, Callable[[], object]] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, name: str, func: Callable[[], object]) -> None:
        if not name:
            raise ValueError("Task name must be non-empty")
        if name in self.tasks:
            raise ValueError(f"Task '{name}' is already registered")
        self.tasks[name] = func
        self.dependencies.setdefault(name, set())
        self.dependents.setdefault(name, set())

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self.tasks or depends_on not in self.tasks:
            raise KeyError("Both tasks must be registered before adding a dependency")
        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)

    def validate(self) -> None:
        state: Dict[str, int] = {name: 0 for name in self.tasks}

        def visit(node: str, path: List[str]) -> None:
            if state[node] == 1:
                raise CycleError(" -> ".join(path + [node]))
            if state[node] == 2:
                return

            state[node] = 1
            for dependency in self.dependencies[node]:
                visit(dependency, path + [node])
            state[node] = 2

        for task_name in self.tasks:
            if state[task_name] == 0:
                visit(task_name, [])

    def get_execution_order(self) -> List[str]:
        self.validate()
        indegree = {task: len(deps) for task, deps in self.dependencies.items()}
        queue = deque(sorted(task for task, degree in indegree.items() if degree == 0))
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in sorted(self.dependents[node]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self.tasks):
            raise CycleError("Cycle detected during topological sort")

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        self.validate()
        indegree = {task: len(deps) for task, deps in self.dependencies.items()}
        available = sorted(task for task, degree in indegree.items() if degree == 0)
        groups: List[Set[str]] = []

        while available:
            group = set(available)
            groups.append(group)
            next_available: List[str] = []

            for node in available:
                for dependent in sorted(self.dependents[node]):
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        next_available.append(dependent)

            available = sorted(set(next_available))

        if sum(len(group) for group in groups) != len(self.tasks):
            raise CycleError("Cycle detected while computing parallel groups")

        return groups

    def execute(self) -> Dict[str, object]:
        self.validate()
        results: Dict[str, object] = {}

        for group in self.get_parallel_groups():
            ordered_group = sorted(group)
            with ThreadPoolExecutor(max_workers=len(ordered_group) or 1) as executor:
                future_map = {executor.submit(self.tasks[name]): name for name in ordered_group}
                for future, name in future_map.items():
                    results[name] = future.result()

        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()
    scheduler.add_task("fetch", lambda: "fetch")
    scheduler.add_task("transform", lambda: "transform")
    scheduler.add_task("load", lambda: "load")
    scheduler.add_dependency("transform", "fetch")
    scheduler.add_dependency("load", "transform")
    print(scheduler.get_execution_order())
    print(scheduler.get_parallel_groups())
    print(scheduler.execute())
