"""Plugin-based Data Pipeline — MC-PY-01 (H × RRR)"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, runtime_checkable

# ── Protocol Interface ──
@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, context: PipelineContext) -> PipelineContext:
        ...

    def should_run(self, context: PipelineContext) -> bool:
        ...

# ── Data Containers ──
@dataclass
class PluginError:
    plugin_name: str
    error_type: str
    message: str
    traceback_str: str

@dataclass
class PipelineContext:
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[PluginError] = field(default_factory=list)

@dataclass
class PluginExecResult:
    plugin_name: str
    status: Literal["success", "skipped", "failed"]
    error: str | None
    duration_ms: float

@dataclass
class PipelineResult:
    success: bool
    context: PipelineContext
    plugin_results: list[PluginExecResult]

# ── Plugin Registry ──
class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: list[TransformPlugin] = []
        self._names: set[str] = set()

    def register(self, plugin_class: type) -> None:
        instance: Any = plugin_class()
        if not isinstance(instance, TransformPlugin):
            return
        name: str = instance.name
        if name in self._names:
            return
        self._names.add(name)
        self._plugins.append(instance)

    def get_plugins(self) -> list[TransformPlugin]:
        return list(self._plugins)

    def clear(self) -> None:
        self._plugins.clear()
        self._names.clear()

# ── Pipeline ──
class Pipeline:
    def __init__(self) -> None:
        self._registry: PluginRegistry = PluginRegistry()

    def load_plugin(self, file_path: str) -> None:
        path: Path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Plugin file not found: {file_path}")

        source: str = path.read_text(encoding="utf-8")
        namespace: dict[str, Any] = {"__builtins__": __builtins__}

        exec(source, namespace)

        # Discover plugin classes
        for obj_name, obj in namespace.items():
            if obj_name.startswith("_"):
                continue
            if isinstance(obj, type) and obj_name != "type":
                # Check if it has the required attributes
                if hasattr(obj, "name") or hasattr(obj, "transform"):
                    try:
                        instance = obj()
                        if hasattr(instance, "name") and hasattr(instance, "transform"):
                            self._registry.register(obj)
                    except Exception:
                        pass

    def register(self, plugin_class: type) -> None:
        self._registry.register(plugin_class)

    def run(self, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> PipelineResult:
        context: PipelineContext = PipelineContext(
            data=dict(data),
            metadata=metadata or {},
        )

        plugin_results: list[PluginExecResult] = []
        all_success: bool = True

        for plugin in self._registry.get_plugins():
            # Check conditional execution
            should_execute: bool = True
            if hasattr(plugin, "should_run"):
                try:
                    should_execute = plugin.should_run(context)
                except Exception:
                    should_execute = True

            if not should_execute:
                plugin_results.append(
                    PluginExecResult(
                        plugin_name=plugin.name,
                        status="skipped",
                        error=None,
                        duration_ms=0.0,
                    )
                )
                continue

            # Execute plugin with error isolation
            start_time: float = time.perf_counter()
            try:
                context = plugin.transform(context)
                elapsed_ms: float = (time.perf_counter() - start_time) * 1000
                plugin_results.append(
                    PluginExecResult(
                        plugin_name=plugin.name,
                        status="success",
                        error=None,
                        duration_ms=round(elapsed_ms, 2),
                    )
                )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                tb_str: str = traceback.format_exc()
                error_msg: str = f"{type(exc).__name__}: {exc}"

                context.errors.append(
                    PluginError(
                        plugin_name=plugin.name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        traceback_str=tb_str,
                    )
                )

                plugin_results.append(
                    PluginExecResult(
                        plugin_name=plugin.name,
                        status="failed",
                        error=error_msg,
                        duration_ms=round(elapsed_ms, 2),
                    )
                )
                all_success = False

        return PipelineResult(
            success=all_success,
            context=context,
            plugin_results=plugin_results,
        )

# ── Example Built-in Plugins (for demonstration / testing) ──

class UpperCasePlugin:
    name: str = "uppercase_transform"

    def transform(self, context: PipelineContext) -> PipelineContext:
        for key, value in context.data.items():
            if isinstance(value, str):
                context.data[key] = value.upper()
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return True

class FilterNullsPlugin:
    name: str = "filter_nulls"

    def transform(self, context: PipelineContext) -> PipelineContext:
        context.data = {k: v for k, v in context.data.items() if v is not None}
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return True

class AddTimestampPlugin:
    name: str = "add_timestamp"

    def transform(self, context: PipelineContext) -> PipelineContext:
        context.metadata["processed_at"] = time.time()
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return "skip_timestamp" not in context.metadata

class RecordCountPlugin:
    name: str = "record_count"

    def transform(self, context: PipelineContext) -> PipelineContext:
        records: Any = context.data.get("records", [])
        if isinstance(records, list):
            context.metadata["record_count"] = len(records)
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return "records" in context.data


# ── Main (demo) ──
if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.register(FilterNullsPlugin)
    pipeline.register(UpperCasePlugin)
    pipeline.register(AddTimestampPlugin)
    pipeline.register(RecordCountPlugin)

    sample_data: dict[str, Any] = {
        "name": "Alice",
        "email": "alice@example.com",
        "role": None,
        "records": [{"id": 1}, {"id": 2}, {"id": 3}],
    }

    result: PipelineResult = pipeline.run(sample_data)

    print(f"Success: {result.success}")
    print(f"Data: {result.context.data}")
    print(f"Metadata: {result.context.metadata}")
    print(f"Errors: {result.context.errors}")
    for pr in result.plugin_results:
        print(f"  {pr.plugin_name}: {pr.status} ({pr.duration_ms}ms)")
