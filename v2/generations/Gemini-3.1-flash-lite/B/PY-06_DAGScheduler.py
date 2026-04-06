class DAGScheduler:
    def __init__(self):
        self.tasks = {}
        self.dependencies = {}

    def add_task(self, name, func):
        self.tasks[name] = func
        if name not in self.dependencies: self.dependencies[name] = set()

    def add_dependency(self, task, depends_on):
        self.dependencies[task].add(depends_on)

    def validate(self):
        # Cycle detection
        for task in self.tasks:
            visited = set()
            stack = [task]
            while stack:
                curr = stack.pop()
                if curr in visited: raise Exception("Cycle detected")
                visited.add(curr)
                stack.extend(self.dependencies.get(curr, []))

    def get_execution_order(self):
        order = []
        visited = set()
        def visit(n):
            if n not in visited:
                for dep in self.dependencies.get(n, []): visit(dep)
                visited.add(n)
                order.append(n)
        for task in self.tasks: visit(task)
        return order

    def execute(self):
        for task in self.get_execution_order():
            self.tasks[task]()
