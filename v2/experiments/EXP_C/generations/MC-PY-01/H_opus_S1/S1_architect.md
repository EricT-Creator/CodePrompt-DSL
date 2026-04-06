# Technical Design Document: Plugin-based Data Pipeline

**Task**: MC-PY-01  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]PY310 [D]STDLIB_ONLY [!D]NO_IMPORTLIB [PLUGIN]EXEC [!D]NO_ABC [IFACE]PROTOCOL [TYPE]FULL_HINTS [ERR]ISOLATE [O]CLASS [FILE]SINGLE`

---

## 1. Pipeline Class Architecture

### Class Hierarchy

```
Pipeline                    (orchestrator — loads and runs plugins)
├── PluginRegistry          (stores discovered plugin classes)
├── PipelineContext         (data container passed through stages)
└── PipelineResult          (execution summary with per-plugin status)
```

### Pipeline Class

The `Pipeline` class is the central orchestrator:

- **Responsibilities**: Load plugin files, instantiate plugins, execute them in sequence, handle conditional branches, isolate errors.
- **Public API**:
  - `load_plugin(file_path: str) -> None` — loads a plugin from a `.py` file.
  - `register(plugin_class: type) -> None` — manually registers a plugin class.
  - `run(data: dict[str, Any]) -> PipelineResult` — executes all registered plugins in order.

### PipelineContext

A mutable data container that flows through all plugins:

```python
@dataclass
class PipelineContext:
    data: dict[str, Any]          # the working dataset
    metadata: dict[str, Any]      # pipeline-level metadata (timestamps, source info)
    errors: list[PluginError]     # accumulated errors from failed plugins
```

### PipelineResult

```python
@dataclass
class PipelineResult:
    success: bool                          # True if all plugins succeeded
    context: PipelineContext               # final state of context
    plugin_results: list[PluginExecResult] # per-plugin outcome
```

```python
@dataclass
class PluginExecResult:
    plugin_name: str
    status: Literal["success", "skipped", "failed"]
    error: str | None
    duration_ms: float
```

---

## 2. Plugin Loading Mechanism (exec Flow)

### Why exec?

The constraint `[PLUGIN]EXEC` mandates using `exec()` for dynamic plugin loading instead of `importlib`. This means plugins are loaded by reading the file as a string and executing it in a controlled namespace.

### Loading Flow

```
1. Read plugin file: source = open(file_path).read()
2. Prepare namespace: namespace = {"__builtins__": __builtins__}
3. Execute: exec(source, namespace)
4. Scan namespace for classes implementing TransformPlugin protocol
5. Register discovered classes in PluginRegistry
```

### Security Considerations

- The `namespace` dict limits what the plugin code can access.
- `__builtins__` is explicitly provided (not stripped) because plugins need basic Python builtins.
- In a production system, this would be sandboxed further; for this design, we accept that `exec` has inherent risks.

### Plugin Discovery

After `exec()`, iterate the namespace looking for classes that satisfy the `TransformPlugin` protocol:

```python
for name, obj in namespace.items():
    if isinstance(obj, type) and hasattr(obj, 'transform') and hasattr(obj, 'name'):
        registry.register(obj)
```

---

## 3. Protocol Interface Definition

### Protocol (not ABC)

Per the `[IFACE]PROTOCOL` constraint, the plugin interface uses `typing.Protocol` (structural subtyping) instead of `abc.ABC` (nominal subtyping):

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, context: PipelineContext) -> PipelineContext:
        """Transform data in the context. Return the modified context."""
        ...

    def should_run(self, context: PipelineContext) -> bool:
        """Conditional execution check. Return True to run, False to skip."""
        ...
```

### Why Protocol over ABC

- Plugins loaded via `exec()` have no way to explicitly inherit from an ABC defined in the main module (they run in an isolated namespace).
- `Protocol` with `@runtime_checkable` allows structural type checking: any class with `name`, `transform()`, and `should_run()` methods automatically satisfies the interface.
- This is the idiomatic Python 3.10+ approach for plugin systems.

### Default Behavior

If a plugin lacks `should_run`, the pipeline treats it as always-run. The protocol's `should_run` is optional in practice — the pipeline checks `hasattr` before calling.

---

## 4. Conditional Branch Design

### Mechanism

Each plugin can define a `should_run(context: PipelineContext) -> bool` method. Before execution, the pipeline calls `should_run`:

```python
for plugin in self.plugins:
    if hasattr(plugin, 'should_run') and not plugin.should_run(context):
        result.append(PluginExecResult(plugin.name, "skipped", None, 0))
        continue
    # execute plugin...
```

### Branch Patterns

Plugins can implement arbitrary conditions based on context data:

- **Data presence**: `return "users" in context.data`
- **Threshold**: `return len(context.data.get("records", [])) > 100`
- **Flag**: `return context.metadata.get("enable_enrichment", False)`
- **Previous error**: `return len(context.errors) == 0` (only run if no prior errors)

### Execution Order

Plugins run in **registration order** (the order they were loaded/registered). There is no dependency graph between plugins — ordering is explicit and determined by the pipeline configuration.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Python 3.10+ | `[L]PY310` | Uses Python 3.10 features: `match` statements (optional), `X \| Y` union syntax, `@dataclass`. |
| Stdlib only | `[D]STDLIB_ONLY` | No pip packages. Only `typing`, `dataclasses`, `time`, `pathlib`, `traceback` from stdlib. |
| No importlib | `[!D]NO_IMPORTLIB` | Plugin loading uses `exec()` with file read, not `importlib.import_module()`. |
| Plugin loading via exec | `[PLUGIN]EXEC` | `exec(source_code, namespace)` is the sole mechanism for loading external plugin files. |
| No ABC | `[!D]NO_ABC` | No `abc.ABC` or `abc.abstractmethod`. Plugin interface defined with `typing.Protocol`. |
| Interface via Protocol | `[IFACE]PROTOCOL` | `TransformPlugin(Protocol)` with `@runtime_checkable` for structural subtyping. |
| Full type hints | `[TYPE]FULL_HINTS` | All functions, methods, class attributes, and return types are fully annotated. |
| Error isolation | `[ERR]ISOLATE` | Each plugin runs inside a `try/except`. Failures are logged in `PipelineContext.errors` but do not halt the pipeline. |
| Class-based output | `[O]CLASS` | Pipeline, PluginRegistry, PipelineContext, PipelineResult are all classes. |
| Single file | `[FILE]SINGLE` | All classes and the main pipeline logic in one `.py` file. |
