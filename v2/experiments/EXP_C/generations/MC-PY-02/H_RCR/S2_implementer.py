from __future__ import annotations
import asyncio
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CycleError(Exception):
    def __init__(self, cycle_nodes: List[str]) -> None:
        self.cycle_nodes = cycle_nodes
        super().__init__(f"Cycle detected involving nodes: {', '.join(cycle_nodes)}")


@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)


class DAG:
    def __init__(self) -> None:
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._in_degree: Dict[str, int] = defaultdict(int)
        self._nodes: Dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        self._nodes[node.name] = node
        if node.name not in self._in_degree:
            self._in_degree[node.name] = 0

    def add_edge(self, from_task: str, to_task: str) -> None:
        if from_task not in self._nodes:
            raise ValueError(f"Task '{from_task}' does not exist")
        if to_task not in self._nodes:
            raise ValueError(f"Task '{to_task}' does not exist")

        if to_task not in self._adjacency[from_task]:
            self._adjacency[from_task].add(to_task)
            self._in_degree[to_task] += 1

    def get_node(self, name: str) -> Optional[TaskNode]:
        return self._nodes.get(name)

    def get_nodes(self) -> List[str]:
        return list(self._nodes.keys())

    def validate(self) -> None:
        groups = self.topological_sort_grouped()
        total_processed = sum(len(g) for g in groups)
        if total_processed < len(self._nodes):
            remaining = [n for n in self._nodes if self._in_degree[n] > 0]
            raise CycleError(remaining)

    def topological_sort_grouped(self) -> List[List[str]]:
        in_degree = dict(self._in_degree)
        current_wave = [n for n in self._nodes if in_degree[n] == 0]
        groups: List[List[str]] = []

        while current_wave:
            groups.append(current_wave.copy())
            next_wave: List[str] = []

            for node in current_wave:
                for successor in self._adjacency[node]:
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_wave.append(successor)

            current_wave = next_wave

        return groups


class DAGScheduler:
    def __init__(self, parallel: bool = False, max_workers: int = 4) -> None:
        self._dag = DAG()
        self._parallel = parallel
        self._max_workers = max_workers

    def add_task(self, name: str, callable: Callable[[], Any], dependencies: Optional[List[str]] = None) -> None:
        node = TaskNode(name=name, callable=callable, dependencies=dependencies or [])
        self._dag.add_node(node)

        for dep in (dependencies or []):
            self._dag.add_edge(dep, name)

    def add_dependency(self, from_task: str, to_task: str) -> None:
        self._dag.add_edge(from_task, to_task)

    def validate(self) -> None:
        self._dag.validate()

    def topological_sort(self) -> List[str]:
        groups = self._dag.topological_sort_grouped()
        result: List[str] = []
        for group in groups:
            result.extend(group)
        return result

    def topological_sort_grouped(self) -> List[List[str]]:
        return self._dag.topological_sort_grouped()

    def _execute_group_sequential(self, group: List[str]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for task_name in group:
            node = self._dag.get_node(task_name)
            if node:
                results[task_name] = node.callable()
        return results

    def _execute_group_parallel(self, group: List[str]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for task_name in group:
                node = self._dag.get_node(task_name)
                if node:
                    futures[executor.submit(node.callable)] = task_name

            for future in futures:
                task_name = futures[future]
                try:
                    results[task_name] = future.result()
                except Exception as e:
                    results[task_name] = e
        return results

    def execute(self) -> Dict[str, Any]:
        self.validate()
        groups = self._dag.topological_sort_grouped()
        all_results: Dict[str, Any] = {}

        for group in groups:
            if self._parallel:
                group_results = self._execute_group_parallel(group)
            else:
                group_results = self._execute_group_sequential(group)
            all_results.update(group_results)

        return all_results

    async def execute_async(self) -> Dict[str, Any]:
        self.validate()
        groups = self._dag.topological_sort_grouped()
        all_results: Dict[str, Any] = {}

        for group in groups:
            tasks = []
            for task_name in group:
                node = self._dag.get_node(task_name)
                if node:
                    async def run_task(n=node, tn=task_name):
                        if asyncio.iscoroutinefunction(n.callable):
                            return tn, await n.callable()
                        else:
                            return tn, n.callable()
                    tasks.append(run_task())

            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in group_results:
                if isinstance(result, tuple):
                    all_results[result[0]] = result[1]
                else:
                    pass

        return all_results
