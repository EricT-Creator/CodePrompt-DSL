class DAGScheduler:
    def __init__(self):
        self.tasks = {}
        self.dependencies = {}

    def add_task(self, name, fn, depends_on=[]):
        self.tasks[name] = fn
        self.dependencies[name] = depends_on

    def _topological_sort(self):
        visited = set()
        stack = []
        path = set()

        def visit(node):
            if node in path:
                raise Exception(f"Cycle detected at {node}")
            if node not in visited:
                path.add(node)
                for dep in self.dependencies.get(node, []):
                    visit(dep)
                path.remove(node)
                visited.add(node)
                stack.append(node)

        for name in self.tasks:
            visit(name)
        return stack

    def execute(self):
        order = self._topological_sort()
        results = {}
        for name in order:
            deps = self.dependencies.get(name, [])
            args = [results[d] for d in deps]
            results[name] = self.tasks[name](*args)
        return order, results
