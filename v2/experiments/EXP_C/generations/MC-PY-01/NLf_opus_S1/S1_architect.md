# Technical Design Document — Plugin-Based ETL Data Pipeline

## 1. Overview

This document describes the architecture for a plugin-based ETL data pipeline. Plugins implement a unified transform interface defined via `typing.Protocol`. The pipeline loads plugins at runtime via `exec()`, runs them in sequence, supports conditional branches where some plugins only execute when a condition is met, and isolates errors so that one plugin failure does not crash the entire pipeline.

## 2. Pipeline Class Architecture

### 2.1 Main Class: Pipeline

The `Pipeline` class is the central orchestrator. Its responsibilities:

- Load plugin files from a specified directory or list of file paths.
- Register loaded plugins in execution order.
- Execute plugins sequentially, passing data through the chain.
- Evaluate conditional predicates before executing conditional plugins.
- Catch and isolate plugin errors, logging failures and continuing execution.

### 2.2 Public Interface

- `Pipeline(config: PipelineConfig)` — Constructor. Accepts configuration for plugin paths, logging, and error behavior.
- `load_plugin(file_path: str) -> None` — Reads a plugin file and loads it via `exec()`.
- `load_plugins(directory: str) -> None` — Loads all `.py` files from a directory in alphabetical order.
- `register(plugin: TransformPlugin, condition: Callable[[dict], bool] | None = None) -> None` — Manually registers a plugin with an optional condition.
- `execute(data: dict) -> PipelineResult` — Runs the pipeline on input data, returns the result.

### 2.3 Supporting Classes

- **PluginRegistry**: Internal list of `(plugin, condition)` tuples maintaining execution order.
- **PipelineResult**: `{ success: bool; data: dict; errors: list[PluginError]; skipped: list[str] }`
- **PluginError**: `{ plugin_name: str; error_type: str; message: str; traceback: str }`

## 3. Plugin Loading Mechanism (exec Flow)

### 3.1 Loading Steps

1. Read the plugin file contents: `source = Path(file_path).read_text()`.
2. Create a namespace dictionary: `namespace = {}`.
3. Execute the file in the namespace: `exec(source, namespace)`.
4. Scan the namespace for any class that satisfies the `TransformPlugin` protocol (has a `transform` method with the correct signature).
5. Instantiate the plugin class: `plugin = PluginClass()`.
6. Register the plugin in the pipeline.

### 3.2 Discovery Heuristic

After `exec()`, iterate over `namespace.values()`. For each value, check:
- Is it a class (not an instance)?
- Does it have a `transform` method?
- Does `transform` accept `(self, data: dict) -> dict`?

If multiple qualifying classes exist in one file, only the first is loaded (or all, configurable).

### 3.3 Error Isolation During Loading

If `exec()` raises an exception (syntax error, import error, etc.), the error is caught, logged as a `PluginError`, and the pipeline continues loading remaining plugins. The failed plugin is not registered.

## 4. Protocol Interface Definition

### 4.1 TransformPlugin Protocol

```
class TransformPlugin(Protocol):
    name: str
    
    def transform(self, data: dict) -> dict:
        ...
```

### 4.2 Design Rationale

Using `typing.Protocol` provides structural subtyping. Plugin authors do not need to inherit from a base class — they only need to implement the required attributes and methods. This is more flexible than ABC and aligns with Python's duck-typing philosophy.

### 4.3 Plugin Metadata

Each plugin exposes:
- `name: str` — Human-readable identifier used in logging and error reporting.
- `transform(self, data: dict) -> dict` — The core transformation function. Receives a data dictionary and returns a (potentially modified) data dictionary.

## 5. Conditional Branch Design

### 5.1 Condition Functions

Each plugin can be registered with an optional condition: a callable `(dict) -> bool` that receives the current pipeline data and returns whether the plugin should execute.

### 5.2 Evaluation

During `execute()`, before running each plugin:
1. If `condition is None`: always execute.
2. If `condition is not None`: call `condition(current_data)`.
   - If `True`: execute the plugin.
   - If `False`: skip the plugin, record its name in `skipped`.

### 5.3 Condition Examples

- A "CSV parser" plugin runs only if `data.get("format") == "csv"`.
- A "deduplication" plugin runs only if `data.get("has_duplicates", False)`.
- Conditions are simple Python callables, defined either inline (lambdas) or as standalone functions.

## 6. Error Isolation Strategy

### 6.1 Per-Plugin Try/Except

Each plugin's `transform()` call is wrapped in a `try/except Exception` block:

1. Try: `current_data = plugin.transform(current_data)`
2. Except: Capture the exception, create a `PluginError` record (plugin name, error type, message, traceback string), append to the errors list, and continue with the **previous** data state (data is not modified on failure).

### 6.2 Failure Modes

| Mode | Behavior |
|------|----------|
| `continue` (default) | Log error, skip plugin, continue with unmodified data |
| `abort` (configurable) | Log error, stop pipeline, return partial result |

### 6.3 Guarantees

- One plugin's exception never propagates to other plugins.
- The pipeline always returns a `PipelineResult`, even if all plugins fail.
- Traceback information is captured via `traceback.format_exc()` for debugging.

## 7. Data Flow

```
input_data → [Plugin 1] → [Plugin 2 (skip if condition false)] → [Plugin 3] → ... → output_data
```

Each plugin receives the data dictionary output by the previous plugin (or the original input if it's the first). The pipeline is purely sequential with conditional skips — no parallel branches or fan-out.

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python 3.10+, standard library only | Only stdlib modules are used: `typing`, `pathlib`, `traceback`, `dataclasses`. No external packages. |
| 2 | No importlib for plugin loading; use exec() | Plugins are loaded by reading file contents and calling `exec(source, namespace)`. The `importlib` module is not imported or used. |
| 3 | No ABC; use typing.Protocol | The `TransformPlugin` interface is defined as a `typing.Protocol` subclass. No `abc.ABC` or `abc.abstractmethod` is used. |
| 4 | Full type annotations on all public methods | All public methods of `Pipeline`, `TransformPlugin`, `PipelineResult`, and `PluginError` have complete type annotations including parameter types and return types. |
| 5 | Plugin errors must be isolated; one failure must not crash the pipeline | Each plugin execution is wrapped in `try/except`. Errors are recorded in `PluginError` dataclass instances. The pipeline continues after a failure. |
| 6 | Single Python file with Pipeline class as main output | Everything — Protocol, Pipeline, dataclasses, plugin loading logic — is in one `.py` file. `Pipeline` is the primary export. |
