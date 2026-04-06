from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable


# ── Protocol Interface ──

@runtime_checkable
class TransformPlugin(Protocol):
    def transform(self, data: Any) -> Any: ...


# ── Result Types ──

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


# ── Pipeline Step ──

@dataclass
class PipelineStep:
    plugin: TransformPlugin
    name: str
    condition: Callable[[Any], bool] | None = None


# ── Pipeline ──

class Pipeline:
    def __init__(self, halt_on_error: bool = False) -> None:
        self.steps: list[PipelineStep] = []
        self.halt_on_error: bool = halt_on_error

    def add_step(self, step: PipelineStep) -> None:
        self.steps.append(step)

    def load_plugin(self, source: str, name: str = "Plugin") -> TransformPlugin:
        namespace: dict[str, Any] = {}
        exec(source, namespace)

        plugin_class = namespace.get(name)
        if plugin_class is None:
            raise ValueError(f"Plugin class '{name}' not found in provided source code")

        instance = plugin_class()

        if not isinstance(instance, TransformPlugin):
            raise TypeError(f"Plugin class '{name}' does not satisfy TransformPlugin protocol")

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

            start_time: float = time.perf_counter()
            report = StepReport(name=step.name, success=False, duration_ms=0.0)

            try:
                if hasattr(step.plugin, "validate") and callable(step.plugin.validate):
                    if not step.plugin.validate(current_data):
                        raise ValueError(f"Validation failed for step '{step.name}'")

                current_data = step.plugin.transform(current_data)
                report.success = True

            except Exception as e:
                report.success = False
                report.error = str(e)
                result.errors.append(
                    StepError(
                        step_name=step.name,
                        exception_type=type(e).__name__,
                        message=str(e),
                    )
                )

                if self.halt_on_error:
                    end_time = time.perf_counter()
                    report.duration_ms = (end_time - start_time) * 1000
                    result.steps_executed.append(report)
                    break

            end_time = time.perf_counter()
            report.duration_ms = (end_time - start_time) * 1000
            result.steps_executed.append(report)

        result.output = current_data
        return result


# ── Built-in Plugins for Demonstration ──

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
        return data


class MultiplyPlugin:
    def __init__(self, factor: int = 2) -> None:
        self.factor: int = factor

    def transform(self, data: Any) -> Any:
        if isinstance(data, (int, float)):
            return data * self.factor
        if isinstance(data, list):
            return [item * self.factor if isinstance(item, (int, float)) else item for item in data]
        return data


# ── Example Usage ──

if __name__ == "__main__":
    pipeline = Pipeline(halt_on_error=False)

    pipeline.add_step(PipelineStep(
        plugin=FilterNonePlugin(),
        name="filter_none",
    ))

    pipeline.add_step(PipelineStep(
        plugin=UpperCasePlugin(),
        name="uppercase",
        condition=lambda data: isinstance(data, (str, list)),
    ))

    plugin_source = """
class Plugin:
    def transform(self, data):
        if isinstance(data, list):
            return sorted(data)
        return data
"""
    sort_plugin = pipeline.load_plugin(plugin_source)
    pipeline.add_step(PipelineStep(
        plugin=sort_plugin,
        name="sort_plugin",
    ))

    test_data: list[str | None] = ["banana", None, "apple", "cherry", None, "date"]
    result = pipeline.run(test_data)

    print(f"Output: {result.output}")
    print(f"Steps executed: {len(result.steps_executed)}")
    print(f"Steps skipped: {result.steps_skipped}")
    print(f"Errors: {result.errors}")

    for report in result.steps_executed:
        status = "OK" if report.success else "FAIL"
        print(f"  [{status}] {report.name} ({report.duration_ms:.2f}ms)")
        if report.error:
            print(f"         Error: {report.error}")
