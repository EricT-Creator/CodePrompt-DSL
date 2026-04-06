class CycleError(Exception): pass

class DAGScheduler:
    def __init__(self):
        self.tasks = {}
        self.dependencies = {}

    def add_task(self, name, func): self.tasks[name] = func
    def add_dependency(self, task, depends_on):
        if task not in self.dependencies: self.dependencies[task] = []
        self.dependencies[task].append(depends_on)

    def validate(self):
        visited = set()
        stack = set()
        def dfs(node):
            if node in stack: raise CycleError()
            if node not in visited:
                stack.add(node)
                for dep in self.dependencies.get(node, []): dfs(dep)
                stack.remove(node)
                visited.add(node)
        for task in self.tasks: dfs(task)

    def get_execution_order(self):
        self.validate()
        order = []
        visited = set()
        def dfs(node):
            if node not in visited:
                for dep in self.dependencies.get(node, []): dfs(dep)
                visited.add(node)
                order.append(node)
        for task in self.tasks: dfs(task)
        return order

    def execute(self):
        order = self.get_execution_order()
        for task in order: self.tasks[task]()
