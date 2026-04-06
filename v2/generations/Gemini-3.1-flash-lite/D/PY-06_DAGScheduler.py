class CycleError(Exception): pass

class DAGScheduler:
    def __init__(self):
        self.tasks = {}
        self.deps = {}

    def add_task(self, name, func):
        self.tasks[name] = func
        self.deps[name] = set()

    def add_dependency(self, task, dep):
        self.deps[task].add(dep)

    def validate(self):
        visited = set()
        path = set()
        def visit(n):
            if n in path: raise CycleError()
            if n not in visited:
                path.add(n)
                for d in self.deps.get(n, []): visit(d)
                path.remove(n)
                visited.add(n)
        for t in self.tasks: visit(t)

    def get_execution_order(self):
        self.validate()
        order = []
        visited = set()
        def visit(n):
            if n not in visited:
                for d in self.deps.get(n, []): visit(d)
                visited.add(n)
                order.append(n)
        for t in self.tasks: visit(t)
        return order

    def execute(self):
        for t in self.get_execution_order():
            self.tasks[t]()
