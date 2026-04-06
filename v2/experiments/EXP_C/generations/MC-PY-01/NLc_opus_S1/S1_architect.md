# Technical Design Document — Plugin-Based ETL Data Pipeline

## 1. Overview

A plugin-based ETL (Extract-Transform-Load) data pipeline where plugins implement a unified transform interface defined by a `Protocol`. Plugins are loaded at runtime via `exec()`, executed in sequence with conditional branching support, and isolated so that one plugin's failure does not crash the entire pipeline.

## 2. Pipeline Class Architecture

### Core Classes

#### `Pipeline`
- The main orchestrator. Holds the ordered list of pipeline steps and executes them sequentially.
- Methods:
  - `add_step(step: PipelineStep)`: append a step to the execution plan.
  - `run(data: Any) -> PipelineResult`: execute all steps in order, passing data through.
  - `load_plugin(source: str) -> TransformPlugin`: load a plugin from source code string via `exec()`.

#### `PipelineStep`
- Wraps a plugin with optional execution metadata.
- Fields: `plugin: TransformPlugin`, `name: str`, `condition: Callable[[Any], bool] | None`.
- If `condition` is provided, the plugin only runs when `condition(data)` returns `True`.

#### `PipelineResult`
- Aggregates the final output and per-step execution reports.
- Fields: `output: Any`, `steps_executed: list[StepReport]`, `steps_skipped: list[str]`, `errors: list[StepError]`.

#### `StepReport`
- Per-step execution record: `name: str`, `success: bool`, `duration_ms: float`, `error: str | None`.

#### `StepError`
- Error detail: `step_name: str`, `exception_type: str`, `message: str`.

## 3. Plugin Loading Mechanism

### exec() Flow

1. Plugin source code is a Python string (read from a file or provided inline).
2. A fresh namespace dict is created: `namespace = {}`.
3. `exec(source_code, namespace)` executes the code into that namespace.
4. The pipeline looks for a well-known name in the namespace — e.g., `namespace["Plugin"]` — which must be a class satisfying the `TransformPlugin` protocol.
5. An instance is created: `plugin = namespace["Plugin"]()`.
6. The instance is wrapped in a `PipelineStep` and added to the pipeline.

### Why exec() (per constraint)
- `importlib` is disallowed. `exec()` is the designated dynamic loading mechanism.
- The namespace isolation means plugin code cannot accidentally pollute the pipeline's global scope.

### Plugin Discovery Convention
- Each plugin source must define a class named `Plugin` at module level.
- The class must have a `transform(self, data: Any) -> Any` method.

## 4. Protocol Interface Definition

### TransformPlugin Protocol

```
class TransformPlugin(Protocol):
    def transform(self, data: Any) -> Any: ...
```

- Uses `typing.Protocol` (structural subtyping), not `abc.ABC`.
- Any class with a `transform(self, data) -> Any` method satisfies the protocol — no inheritance required.
- This enables loose coupling: plugins do not need to import or inherit from a base class.

### Optional Extension Points
- `def validate(self, data: Any) -> bool`: pre-check if the plugin can handle the incoming data shape.
- `def name(self) -> str`: human-readable plugin identifier.

These are optional — the pipeline checks for their existence via `hasattr` before calling.

## 5. Conditional Branch Design

### Mechanism
Each `PipelineStep` carries an optional `condition: Callable[[Any], bool]`.

### Execution Logic
```
for step in self.steps:
    if step.condition is not None and not step.condition(current_data):
        result.steps_skipped.append(step.name)
        continue
    # execute step...
```

### Use Cases
- Data-type routing: only run a CSV parser plugin if the data is a string.
- Volume thresholds: only run an aggregation plugin if `len(data) > 1000`.
- Feature flags: condition checks an external config dict.

### Branching vs. Full DAG
This design uses linear sequential execution with conditional skips, not a full DAG. This is simpler and sufficient for the stated requirements. A future extension could support named branches and merge points.

## 6. Error Isolation

### Strategy
Each plugin runs inside a `try / except Exception` block:

```
try:
    current_data = step.plugin.transform(current_data)
    report.success = True
except Exception as e:
    report.success = False
    report.error = str(e)
    result.errors.append(StepError(...))
    # current_data is unchanged — pipeline continues with previous data
```

### Key Properties
- **Non-fatal**: a failed plugin does not raise to the caller or abort the pipeline.
- **Data passthrough**: on failure, the data from the previous successful step is passed to the next step unchanged.
- **Logging**: the error is captured in `StepReport` and `PipelineResult.errors` for post-run inspection.
- **Optional halt mode**: a configuration flag `halt_on_error: bool` can optionally make the pipeline stop on first failure, but the default is to continue.

## 7. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python 3.10+, stdlib only** | All imports from Python standard library. No third-party packages. |
| 2 | **exec() for plugin loading, no importlib** | Plugins are loaded by executing their source code string via `exec()` into an isolated namespace. `importlib` is not used. |
| 3 | **Protocol for interfaces, no ABC** | `TransformPlugin` is defined as a `typing.Protocol`. No `abc.ABC` or `abc.abstractmethod`. |
| 4 | **Full type annotations** | Every function signature, class attribute, and variable uses type hints. |
| 5 | **Plugin errors isolated** | Each plugin runs inside `try/except`; failures are captured in the result without crashing the pipeline. |
| 6 | **Single file, class output** | All classes, protocols, and pipeline logic reside in a single `.py` file. The main deliverable is the `Pipeline` class. |
