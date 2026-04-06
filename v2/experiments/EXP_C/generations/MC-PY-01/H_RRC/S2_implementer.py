"""Plugin-based Data Pipeline — MC-PY-01 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, runtime_checkable


# ─── Protocol Interface ───


@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, context: PipelineContext) -> PipelineContext:
        ...

    def should_run(self, context: PipelineContext) -> bool:
        ...


# ─── Data Containers ───


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


# ─── Plugin Registry ───


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: list[type] = []

    def register(self, plugin_class: type) -> None:
        if plugin_class not in self._plugins:
            self._plugins.append(plugin_class)

    def get_plugins(self) -> list[type]:
        return list(self._plugins)

    def clear(self) -> None:
        self._plugins.clear()


# ─── Pipeline ───


class Pipeline:
    def __init__(self) -> None:
        self._registry: PluginRegistry = PluginRegistry()
        self._plugin_instances: list[Any] = []

    def load_plugin(self, file_path: str) -> None:
        source: str = Path(file_path).read_text(encoding="utf-8")
        namespace: dict[str, Any] = {"__builtins__": __builtins__}
        exec(source, namespace)

        for name, obj in namespace.items():
            if (
                isinstance(obj, type)
                and obj is not type
                and hasattr(obj, "transform")
                and hasattr(obj, "name")
            ):
                self._registry.register(obj)
                instance = obj()
                self._plugin_instances.append(instance)

    def register(self, plugin_class: type) -> None:
        self._registry.register(plugin_class)
        instance = plugin_class()
        self._plugin_instances.append(instance)

    def run(self, data: dict[str, Any]) -> PipelineResult:
        context = PipelineContext(
            data=dict(data),
            metadata={"start_time": time.time(), "pipeline_version": "1.0"},
        )
        plugin_results: list[PluginExecResult] = []
        all_success: bool = True

        for plugin in self._plugin_instances:
            plugin_name: str = getattr(plugin, "name", plugin.__class__.__name__)

            # Check conditional execution
            if hasattr(plugin, "should_run"):
                try:
                    if not plugin.should_run(context):
                        plugin_results.append(
                            PluginExecResult(
                                plugin_name=plugin_name,
                                status="skipped",
                                error=None,
                                duration_ms=0.0,
                            )
                        )
                        continue
                except Exception as exc:
                    # If should_run itself fails, skip the plugin
                    plugin_results.append(
                        PluginExecResult(
                            plugin_name=plugin_name,
                            status="failed",
                            error=f"should_run failed: {exc}",
                            duration_ms=0.0,
                        )
                    )
                    all_success = False
                    continue

            # Execute plugin with error isolation
            start: float = time.perf_counter()
            try:
                context = plugin.transform(context)
                elapsed_ms: float = (time.perf_counter() - start) * 1000
                plugin_results.append(
                    PluginExecResult(
                        plugin_name=plugin_name,
                        status="success",
                        error=None,
                        duration_ms=round(elapsed_ms, 2),
                    )
                )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                tb_str: str = traceback.format_exc()
                context.errors.append(
                    PluginError(
                        plugin_name=plugin_name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        traceback_str=tb_str,
                    )
                )
                plugin_results.append(
                    PluginExecResult(
                        plugin_name=plugin_name,
                        status="failed",
                        error=str(exc),
                        duration_ms=round(elapsed_ms, 2),
                    )
                )
                all_success = False

        context.metadata["end_time"] = time.time()
        context.metadata["total_plugins"] = len(self._plugin_instances)
        context.metadata["executed"] = sum(
            1 for r in plugin_results if r.status == "success"
        )
        context.metadata["skipped"] = sum(
            1 for r in plugin_results if r.status == "skipped"
        )
        context.metadata["failed"] = sum(
            1 for r in plugin_results if r.status == "failed"
        )

        return PipelineResult(
            success=all_success,
            context=context,
            plugin_results=plugin_results,
        )


# ─── Built-in demo plugins (for testing) ───


class UpperCasePlugin:
    name: str = "uppercase_transformer"

    def transform(self, context: PipelineContext) -> PipelineContext:
        for key in list(context.data.keys()):
            val = context.data[key]
            if isinstance(val, str):
                context.data[key] = val.upper()
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return True


class FilterEmptyPlugin:
    name: str = "filter_empty"

    def transform(self, context: PipelineContext) -> PipelineContext:
        context.data = {
            k: v for k, v in context.data.items() if v is not None and v != ""
        }
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return len(context.data) > 0


class AddTimestampPlugin:
    name: str = "add_timestamp"

    def transform(self, context: PipelineContext) -> PipelineContext:
        context.data["_processed_at"] = time.time()
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return "_processed_at" not in context.data


# ─── Main entry point (demo) ───

if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.register(UpperCasePlugin)
    pipeline.register(FilterEmptyPlugin)
    pipeline.register(AddTimestampPlugin)

    sample_data: dict[str, Any] = {
        "name": "Alice",
        "email": "alice@example.com",
        "empty_field": "",
        "none_field": None,
        "count": 42,
    }

    result: PipelineResult = pipeline.run(sample_data)
    print(f"Success: {result.success}")
    for pr in result.plugin_results:
        print(f"  [{pr.status}] {pr.plugin_name} ({pr.duration_ms}ms)")
    print(f"Final data: {result.context.data}")
