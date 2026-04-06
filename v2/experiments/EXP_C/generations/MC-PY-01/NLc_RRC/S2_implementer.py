from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable


# ─── Protocol Interface ──────────────────────────────────────────────────────

@runtime_checkable
class TransformPlugin(Protocol):
    def transform(self, data: Any) -> Any: ...


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class StepError:
    step_name: str
    exception_type: str
    message: str


@dataclass
class StepReport:
    name: str
    success: bool
    duration_ms: float
    error: str | None = None


@dataclass
class PipelineResult:
    output: Any
    steps_executed: list[StepReport] = field(default_factory=list)
    steps_skipped: list[str] = field(default_factory=list)
    errors: list[StepError] = field(default_factory=list)


@dataclass
class PipelineStep:
    plugin: TransformPlugin
    name: str
    condition: Callable[[Any], bool] | None = None


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class Pipeline:
    def __init__(self, halt_on_error: bool = False) -> None:
        self.steps: list[PipelineStep] = []
        self.halt_on_error: bool = halt_on_error

    def add_step(
        self,
        step: PipelineStep,
    ) -> None:
        self.steps.append(step)

    def load_plugin(self, source: str) -> TransformPlugin:
        namespace: dict[str, Any] = {}
        exec(source, namespace)
        plugin_cls = namespace.get("Plugin")
        if plugin_cls is None:
            raise ValueError("Plugin source must define a class named 'Plugin'")
        instance = plugin_cls()
        if not isinstance(instance, TransformPlugin):
            raise TypeError("Plugin class must implement the TransformPlugin protocol (transform method)")
        return instance

    def run(self, data: Any) -> PipelineResult:
        result = PipelineResult(output=data)
        current_data: Any = data

        for step in self.steps:
            if step.condition is not None:
                try:
                    should_run = step.condition(current_data)
                except Exception:
                    should_run = False
                if not should_run:
                    result.steps_skipped.append(step.name)
                    continue

            report = StepReport(name=step.name, success=False, duration_ms=0.0)
            start_time = time.perf_counter()

            try:
                if hasattr(step.plugin, "validate") and callable(step.plugin.validate):
                    if not step.plugin.validate(current_data):
                        raise ValueError(f"Plugin '{step.name}' validation failed for input data")

                transformed = step.plugin.transform(current_data)
                elapsed = (time.perf_counter() - start_time) * 1000
                report.success = True
                report.duration_ms = round(elapsed, 3)
                current_data = transformed

            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                report.success = False
                report.duration_ms = round(elapsed, 3)
                report.error = str(e)
                result.errors.append(
                    StepError(
                        step_name=step.name,
                        exception_type=type(e).__name__,
                        message=str(e),
                    )
                )
                if self.halt_on_error:
                    result.steps_executed.append(report)
                    break

            result.steps_executed.append(report)

        result.output = current_data
        return result


# ─── Built-in Plugin Examples ─────────────────────────────────────────────────

class UpperCasePlugin:
    def transform(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.upper()
        if isinstance(data, list):
            return [item.upper() if isinstance(item, str) else item for item in data]
        return data


class FilterNonePlugin:
    def transform(self, data: Any) -> Any:
        if isinstance(data, list):
            return [item for item in data if item is not None]
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class MultiplyPlugin:
    def transform(self, data: Any) -> Any:
        if isinstance(data, (int, float)):
            return data * 2
        if isinstance(data, list):
            return [x * 2 if isinstance(x, (int, float)) else x for x in data]
        return data


# ─── Demo / Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = Pipeline()

    plugin_source = '''
class Plugin:
    def transform(self, data):
        if isinstance(data, list):
            return [x for x in data if isinstance(x, (int, float)) and x > 0]
        return data

    def name(self):
        return "PositiveFilter"
'''

    loaded_plugin = pipeline.load_plugin(plugin_source)

    pipeline.add_step(PipelineStep(plugin=FilterNonePlugin(), name="RemoveNones"))
    pipeline.add_step(
        PipelineStep(
            plugin=loaded_plugin,
            name="PositiveFilter",
            condition=lambda d: isinstance(d, list),
        )
    )
    pipeline.add_step(PipelineStep(plugin=MultiplyPlugin(), name="DoubleValues"))

    test_data: list[Any] = [None, 3, -1, None, 7, 0, 12, -5, None, 42]
    result = pipeline.run(test_data)

    print(f"Input:  {test_data}")
    print(f"Output: {result.output}")
    print(f"Steps executed: {len(result.steps_executed)}")
    print(f"Steps skipped:  {len(result.steps_skipped)}")
    print(f"Errors:         {len(result.errors)}")
    for report in result.steps_executed:
        status = "✓" if report.success else "✗"
        print(f"  {status} {report.name}: {report.duration_ms:.2f}ms")
