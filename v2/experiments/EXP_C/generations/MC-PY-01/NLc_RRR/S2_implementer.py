from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable


# ---- Protocol Interface ----

@runtime_checkable
class TransformPlugin(Protocol):
    def transform(self, data: Any) -> Any: ...


# ---- Result Dataclasses ----

@dataclass
class StepReport:
    name: str
    success: bool
    duration_ms: float
    error: str | None = None


@dataclass
class StepError:
    step_name: str
    exception_type: str
    message: str


@dataclass
class PipelineResult:
    output: Any
    steps_executed: list[StepReport] = field(default_factory=list)
    steps_skipped: list[str] = field(default_factory=list)
    errors: list[StepError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# ---- Pipeline Step ----

@dataclass
class PipelineStep:
    plugin: TransformPlugin
    name: str
    condition: Callable[[Any], bool] | None = None


# ---- Pipeline ----

class Pipeline:
    def __init__(self, halt_on_error: bool = False) -> None:
        self.steps: list[PipelineStep] = []
        self.halt_on_error: bool = halt_on_error

    def add_step(
        self,
        step: PipelineStep,
    ) -> None:
        self.steps.append(step)

    def load_plugin(self, source: str, name: str | None = None) -> TransformPlugin:
        namespace: dict[str, Any] = {}
        exec(source, namespace)

        plugin_class = namespace.get("Plugin")
        if plugin_class is None:
            raise ValueError("Plugin source must define a class named 'Plugin'")

        plugin_instance = plugin_class()

        if not isinstance(plugin_instance, TransformPlugin):
            raise TypeError("Plugin class must implement the TransformPlugin protocol (must have a 'transform' method)")

        return plugin_instance

    def add_plugin_from_source(
        self,
        source: str,
        name: str | None = None,
        condition: Callable[[Any], bool] | None = None,
    ) -> None:
        plugin = self.load_plugin(source, name)
        plugin_name = name
        if plugin_name is None:
            if hasattr(plugin, "name") and callable(plugin.name):
                plugin_name = plugin.name()
            else:
                plugin_name = type(plugin).__name__
        step = PipelineStep(plugin=plugin, name=plugin_name, condition=condition)
        self.add_step(step)

    def run(self, data: Any) -> PipelineResult:
        result = PipelineResult(output=data)
        current_data: Any = data

        for step in self.steps:
            # Check condition
            if step.condition is not None:
                try:
                    should_run = step.condition(current_data)
                except Exception:
                    should_run = False
                if not should_run:
                    result.steps_skipped.append(step.name)
                    continue

            # Optional validation
            if hasattr(step.plugin, "validate") and callable(step.plugin.validate):
                try:
                    is_valid = step.plugin.validate(current_data)
                    if not is_valid:
                        result.steps_skipped.append(step.name)
                        continue
                except Exception:
                    pass

            # Execute plugin
            start_time = time.perf_counter()
            report = StepReport(name=step.name, success=False, duration_ms=0.0)

            try:
                current_data = step.plugin.transform(current_data)
                report.success = True
            except Exception as e:
                report.success = False
                report.error = str(e)
                result.errors.append(StepError(
                    step_name=step.name,
                    exception_type=type(e).__name__,
                    message=str(e),
                ))
                if self.halt_on_error:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    report.duration_ms = elapsed
                    result.steps_executed.append(report)
                    break
                # On failure, current_data remains unchanged (passthrough)

            elapsed = (time.perf_counter() - start_time) * 1000
            report.duration_ms = elapsed
            result.steps_executed.append(report)

        result.output = current_data
        return result


# ---- Built-in Example Plugins (for demonstration) ----

class UpperCasePlugin:
    """Converts string data to uppercase."""

    def transform(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.upper()
        if isinstance(data, list):
            return [item.upper() if isinstance(item, str) else item for item in data]
        return data

    def name(self) -> str:
        return "UpperCasePlugin"


class FilterNonePlugin:
    """Removes None values from list data."""

    def transform(self, data: Any) -> Any:
        if isinstance(data, list):
            return [item for item in data if item is not None]
        return data

    def validate(self, data: Any) -> bool:
        return isinstance(data, list)

    def name(self) -> str:
        return "FilterNonePlugin"


class MultiplyPlugin:
    """Multiplies numeric data by a factor."""

    def __init__(self, factor: float = 2.0) -> None:
        self.factor: float = factor

    def transform(self, data: Any) -> Any:
        if isinstance(data, (int, float)):
            return data * self.factor
        if isinstance(data, list):
            return [item * self.factor if isinstance(item, (int, float)) else item for item in data]
        return data

    def name(self) -> str:
        return f"MultiplyPlugin(x{self.factor})"


# ---- Main (demo usage) ----

if __name__ == "__main__":
    # Demo: Build a pipeline with built-in plugins
    pipeline = Pipeline()

    pipeline.add_step(PipelineStep(
        plugin=FilterNonePlugin(),
        name="FilterNones",
        condition=lambda data: isinstance(data, list),
    ))
    pipeline.add_step(PipelineStep(
        plugin=UpperCasePlugin(),
        name="ToUpperCase",
    ))

    result = pipeline.run(["hello", None, "world", None, "python"])
    print(f"Output: {result.output}")
    print(f"Steps executed: {len(result.steps_executed)}")
    print(f"Steps skipped: {result.steps_skipped}")
    print(f"Errors: {result.errors}")

    # Demo: Load a plugin via exec()
    plugin_source = '''
class Plugin:
    def transform(self, data):
        if isinstance(data, list):
            return [s + "!" for s in data if isinstance(s, str)]
        return data

    def name(self):
        return "ExclamationPlugin"
'''

    pipeline2 = Pipeline()
    pipeline2.add_plugin_from_source(plugin_source, name="AddExclamation")
    result2 = pipeline2.run(["hello", "world"])
    print(f"\nPipeline 2 Output: {result2.output}")

    # Demo: Error isolation
    bad_plugin_source = '''
class Plugin:
    def transform(self, data):
        raise ValueError("Intentional error for testing")
'''

    pipeline3 = Pipeline(halt_on_error=False)
    pipeline3.add_plugin_from_source(bad_plugin_source, name="BadPlugin")
    pipeline3.add_step(PipelineStep(
        plugin=UpperCasePlugin(),
        name="ToUpperCase",
    ))
    result3 = pipeline3.run("test data")
    print(f"\nPipeline 3 Output: {result3.output}")
    print(f"Errors: {[e.message for e in result3.errors]}")
    print(f"Success: {result3.success}")
