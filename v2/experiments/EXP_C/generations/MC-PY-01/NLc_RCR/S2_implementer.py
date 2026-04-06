from typing import Any, Callable, Protocol, Optional
from dataclasses import dataclass, field
import time

class TransformPlugin(Protocol):
    def transform(self, data: Any) -> Any: ...

@dataclass
class StepReport:
    name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None

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
    def total_issues(self) -> int:
        return len(self.errors)

@dataclass
class PipelineStep:
    plugin: TransformPlugin
    name: str
    condition: Optional[Callable[[Any], bool]] = None

class Pipeline:
    def __init__(self, halt_on_error: bool = False):
        self.steps: list[PipelineStep] = []
        self.halt_on_error = halt_on_error
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        self.steps.append(step)
        return self
    
    def load_plugin(self, source: str) -> TransformPlugin:
        namespace: dict[str, Any] = {}
        exec(source, namespace)
        if "Plugin" not in namespace:
            raise ValueError("Plugin source must define a 'Plugin' class")
        plugin_class = namespace["Plugin"]
        return plugin_class()
    
    def run(self, data: Any) -> PipelineResult:
        current_data = data
        result = PipelineResult(output=data)
        
        for step in self.steps:
            if step.condition is not None and not step.condition(current_data):
                result.steps_skipped.append(step.name)
                continue
            
            start_time = time.time()
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
                    message=str(e)
                ))
                if self.halt_on_error:
                    report.duration_ms = (time.time() - start_time) * 1000
                    result.steps_executed.append(report)
                    break
            
            report.duration_ms = (time.time() - start_time) * 1000
            result.steps_executed.append(report)
        
        result.output = current_data
        return result
