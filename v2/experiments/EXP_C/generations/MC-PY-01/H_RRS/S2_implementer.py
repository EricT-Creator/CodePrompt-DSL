"""Plugin-based Data Pipeline — MC-PY-01 (H × RRS)"""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, runtime_checkable


# ─── Protocol interface (not ABC) ───
@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, context: PipelineContext) -> PipelineContext:
        ...

    def should_run(self, context: PipelineContext) -> bool:
        ...


# ─── Data containers ───
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

    def get_all(self) -> list[type]:
        return list(self._plugins)

    def clear(self) -> None:
        self._plugins.clear()


# ─── Pipeline ───
class Pipeline:
    def __init__(self) -> None:
        self._registry: PluginRegistry = PluginRegistry()
        self._instances: list[Any] = []

    def load_plugin(self, file_path: str) -> None:
        """Load a plugin from a .py file via exec()."""
        source: str = Path(file_path).read_text(encoding="utf-8")
        namespace: dict[str, Any] = {"__builtins__": __builtins__}

        # Inject types the plugin might need to reference
        namespace["PipelineContext"] = PipelineContext
        namespace["PluginError"] = PluginError

        exec(source, namespace)

        # Discover plugin classes
        for name, obj in namespace.items():
            if (
                isinstance(obj, type)
                and obj is not type
                and hasattr(obj, "transform")
                and hasattr(obj, "name")
            ):
                self._registry.register(obj)
                instance = obj()
                self._instances.append(instance)

    def register(self, plugin_class: type) -> None:
        """Manually register a plugin class."""
        self._registry.register(plugin_class)
        instance = plugin_class()
        self._instances.append(instance)

    def run(self, data: dict[str, Any]) -> PipelineResult:
        """Execute all registered plugins in order."""
        context = PipelineContext(data=data, metadata={"started_at": time.time()})
        results: list[PluginExecResult] = []
        all_success = True

        for plugin in self._instances:
            plugin_name: str = getattr(plugin, "name", plugin.__class__.__name__)

            # Check conditional execution
            if hasattr(plugin, "should_run"):
                try:
                    if not plugin.should_run(context):
                        results.append(
                            PluginExecResult(
                                plugin_name=plugin_name,
                                status="skipped",
                                error=None,
                                duration_ms=0.0,
                            )
                        )
                        continue
                except Exception as exc:
                    # Error in should_run — treat as skipped
                    results.append(
                        PluginExecResult(
                            plugin_name=plugin_name,
                            status="skipped",
                            error=f"should_run error: {exc}",
                            duration_ms=0.0,
                        )
                    )
                    continue

            # Execute with error isolation
            start = time.perf_counter()
            try:
                context = plugin.transform(context)
                elapsed_ms = (time.perf_counter() - start) * 1000
                results.append(
                    PluginExecResult(
                        plugin_name=plugin_name,
                        status="success",
                        error=None,
                        duration_ms=round(elapsed_ms, 3),
                    )
                )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                all_success = False
                tb_str = traceback.format_exc()
                context.errors.append(
                    PluginError(
                        plugin_name=plugin_name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        traceback_str=tb_str,
                    )
                )
                results.append(
                    PluginExecResult(
                        plugin_name=plugin_name,
                        status="failed",
                        error=str(exc),
                        duration_ms=round(elapsed_ms, 3),
                    )
                )

        context.metadata["finished_at"] = time.time()

        return PipelineResult(
            success=all_success,
            context=context,
            plugin_results=results,
        )


# ─── Built-in example plugins (for demonstration / testing) ───

class UpperCasePlugin:
    name: str = "uppercase"

    def transform(self, context: PipelineContext) -> PipelineContext:
        for key, value in context.data.items():
            if isinstance(value, str):
                context.data[key] = value.upper()
        return context

    def should_run(self, context: PipelineContext) -> bool:
        return True


class FilterEmptyPlugin:
    name: str = "filter_empty"

    def transform(self, context: PipelineContext) -> PipelineContext:
        context.data = {k: v for k, v in context.data.items() if v}
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


# ─── Main guard ───
if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.register(UpperCasePlugin)
    pipeline.register(FilterEmptyPlugin)
    pipeline.register(AddTimestampPlugin)

    sample_data: dict[str, Any] = {
        "greeting": "hello world",
        "empty_field": "",
        "count": 42,
    }
    result = pipeline.run(sample_data)
    print(f"Success: {result.success}")
    for pr in result.plugin_results:
        print(f"  [{pr.status}] {pr.plugin_name} ({pr.duration_ms:.2f}ms)")
    print(f"Final data: {result.context.data}")
