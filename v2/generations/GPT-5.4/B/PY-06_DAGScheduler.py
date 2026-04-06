from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Set


class CycleError(Exception):
    pass


@dataclass
class DAGScheduler:
    tasks: Dict[str, Callable[[], object]] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)

    def add_task(self, name: str, func: Callable[[], object]) -> None:
        if not name:
            raise ValueError("Task name cannot be empty")
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        self.tasks[name] = func
        self.dependencies.setdefault(name, set())

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self.tasks:
            raise KeyError(f"Unknown task: {task}")
        if depends_on not in self.tasks:
            raise KeyError(f"Unknown dependency: {depends_on}")
        self.dependencies.setdefault(task, set()).add(depends_on)

    def validate(self) -> None:
        for task_name, dependency_names in self.dependencies.items():
            if task_name not in self.tasks:
                raise KeyError(f"Task '{task_name}' is not registered")
            missing = dependency_names - self.tasks.keys()
            if missing:
                raise KeyError(f"Task '{task_name}' depends on unknown tasks: {sorted(missing)}")

        state: Dict[str, str] = {}
        stack: List[str] = []

        def visit(task_name: str) -> None:
            status = state.get(task_name)
            if status == "visiting":
                cycle_path = stack + [task_name]
                raise CycleError(" -> ".join(cycle_path))
            if status == "visited":
                return

            state[task_name] = "visiting"
            stack.append(task_name)
            for dependency_name in self.dependencies.get(task_name, set()):
                visit(dependency_name)
            stack.pop()
            state[task_name] = "visited"

        for task_name in self.tasks:
            visit(task_name)

    def _indegree_map(self) -> Dict[str, int]:
        indegree = {task_name: 0 for task_name in self.tasks}
        for task_name, dependency_names in self.dependencies.items():
            indegree[task_name] += len(dependency_names)
        return indegree

    def _dependents_map(self) -> Dict[str, Set[str]]:
        dependents = {task_name: set() for task_name in self.tasks}
        for task_name, dependency_names in self.dependencies.items():
            for dependency_name in dependency_names:
                dependents[dependency_name].add(task_name)
        return dependents

    def get_execution_order(self) -> List[str]:
        self.validate()
        indegree = self._indegree_map()
        dependents = self._dependents_map()
        queue = deque(sorted(task_name for task_name, count in indegree.items() if count == 0))
        order: List[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for dependent in sorted(dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self.tasks):
            raise CycleError("Unable to determine execution order because a cycle exists")
        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        self.validate()
        indegree = self._indegree_map()
        dependents = self._dependents_map()
        ready = sorted(task_name for task_name, count in indegree.items() if count == 0)
        groups: List[Set[str]] = []

        while ready:
            current_group = set(ready)
            groups.append(current_group)
            next_ready: List[str] = []

            for task_name in ready:
                for dependent in sorted(dependents[task_name]):
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        next_ready.append(dependent)

            ready = sorted(set(next_ready))

        if sum(len(group) for group in groups) != len(self.tasks):
            raise CycleError("Unable to determine parallel groups because a cycle exists")
        return groups

    def execute(self) -> Dict[str, object]:
        self.validate()
        results: Dict[str, object] = {}
        for task_name in self.get_execution_order():
            results[task_name] = self.tasks[task_name]()
        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()
    scheduler.add_task("fetch", lambda: "fetch done")
    scheduler.add_task("clean", lambda: "clean done")
    scheduler.add_task("train", lambda: "train done")
    scheduler.add_task("report", lambda: "report done")
    scheduler.add_dependency("clean", "fetch")
    scheduler.add_dependency("train", "clean")
    scheduler.add_dependency("report", "train")

    print("Execution order:", scheduler.get_execution_order())
    print("Parallel groups:", scheduler.get_parallel_groups())
    print("Results:", scheduler.execute())
