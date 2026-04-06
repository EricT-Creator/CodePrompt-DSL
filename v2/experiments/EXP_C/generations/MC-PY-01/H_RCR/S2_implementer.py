from __future__ import annotations
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Protocol, runtime_checkable, Optional


@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, context: PipelineContext) -> PipelineContext:
        ...

    def should_run(self, context: PipelineContext) -> bool:
        ...


@dataclass
class PipelineContext:
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[PluginError] = field(default_factory=list)


@dataclass
class PluginError:
    plugin_name: str
    error: str
    traceback: str


@dataclass
class PluginExecResult:
    plugin_name: str
    status: Literal["success", "skipped", "failed"]
    error: Optional[str]
    duration_ms: float


@dataclass
class PipelineResult:
    success: bool
    context: PipelineContext
    plugin_results: List[PluginExecResult]


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: List[type] = []

    def register(self, plugin_class: type) -> None:
        self._plugins.append(plugin_class)

    def get_plugins(self) -> List[type]:
        return self._plugins.copy()

    def clear(self) -> None:
        self._plugins.clear()


class Pipeline:
    def __init__(self) -> None:
        self._registry = PluginRegistry()
        self._instances: List[TransformPlugin] = []

    def load_plugin(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Plugin file not found: {file_path}")

        source = path.read_text()
        namespace: Dict[str, Any] = {"__builtins__": __builtins__}
        exec(source, namespace)

        for name, obj in namespace.items():
            if isinstance(obj, type) and hasattr(obj, 'transform') and hasattr(obj, 'name'):
                if name != "TransformPlugin":
                    self._registry.register(obj)

    def register(self, plugin_class: type) -> None:
        self._registry.register(plugin_class)

    def _instantiate_plugins(self) -> None:
        self._instances = []
        for plugin_class in self._registry.get_plugins():
            try:
                instance = plugin_class()
                self._instances.append(instance)
            except Exception as e:
                pass

    def run(self, data: Dict[str, Any]) -> PipelineResult:
        self._instantiate_plugins()

        context = PipelineContext(data=data.copy())
        results: List[PluginExecResult] = []

        for plugin in self._instances:
            start_time = time.time()
            should_run = True

            if hasattr(plugin, 'should_run'):
                try:
                    should_run = plugin.should_run(context)
                except Exception as e:
                    should_run = True

            if not should_run:
                results.append(PluginExecResult(
                    plugin_name=plugin.name,
                    status="skipped",
                    error=None,
                    duration_ms=0.0
                ))
                continue

            try:
                context = plugin.transform(context)
                duration_ms = (time.time() - start_time) * 1000
                results.append(PluginExecResult(
                    plugin_name=plugin.name,
                    status="success",
                    error=None,
                    duration_ms=duration_ms
                ))
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                tb = traceback.format_exc()
                context.errors.append(PluginError(
                    plugin_name=plugin.name,
                    error=error_msg,
                    traceback=tb
                ))
                results.append(PluginExecResult(
                    plugin_name=plugin.name,
                    status="failed",
                    error=error_msg,
                    duration_ms=duration_ms
                ))

        success = all(r.status == "success" for r in results)

        return PipelineResult(
            success=success,
            context=context,
            plugin_results=results
        )
