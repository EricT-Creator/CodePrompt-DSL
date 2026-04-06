import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TransformPlugin(Protocol):
    name: str
    
    def transform(self, data: dict) -> dict:
        ...


@dataclass
class PluginError:
    plugin_name: str
    error_type: str
    message: str
    traceback: str


@dataclass
class PipelineResult:
    success: bool
    data: dict
    errors: List[PluginError] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    plugin_paths: List[str] = field(default_factory=list)
    error_mode: str = "continue"


class Pipeline:
    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self._registry: List[tuple[TransformPlugin, Optional[Callable[[dict], bool]]]] = []
    
    def load_plugin(self, file_path: str) -> None:
        try:
            source = Path(file_path).read_text()
            namespace: Dict[str, Any] = {}
            exec(source, namespace)
            
            for value in namespace.values():
                if isinstance(value, type) and self._is_plugin_class(value):
                    plugin = value()
                    self.register(plugin)
        except Exception as e:
            error = PluginError(
                plugin_name=file_path,
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc()
            )
            if self.config.error_mode == "abort":
                raise RuntimeError(f"Failed to load plugin {file_path}: {e}")
    
    def _is_plugin_class(self, cls: type) -> bool:
        if not callable(getattr(cls, '__init__', None)):
            return False
        if not hasattr(cls, 'transform'):
            return False
        import inspect
        try:
            sig = inspect.signature(cls.transform)
            params = list(sig.parameters.keys())
            return len(params) >= 2 and params[1] == 'data'
        except (ValueError, TypeError):
            return False
    
    def load_plugins(self, directory: str) -> None:
        path = Path(directory)
        for file_path in sorted(path.glob("*.py")):
            self.load_plugin(str(file_path))
    
    def register(self, plugin: TransformPlugin, condition: Optional[Callable[[dict], bool]] = None) -> None:
        self._registry.append((plugin, condition))
    
    def execute(self, data: dict) -> PipelineResult:
        current_data = data.copy()
        errors: List[PluginError] = []
        skipped: List[str] = []
        
        for plugin, condition in self._registry:
            if condition is not None:
                try:
                    should_run = condition(current_data)
                except Exception as e:
                    should_run = False
                if not should_run:
                    skipped.append(plugin.name)
                    continue
            
            try:
                current_data = plugin.transform(current_data)
            except Exception as e:
                error = PluginError(
                    plugin_name=plugin.name,
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback=traceback.format_exc()
                )
                errors.append(error)
                if self.config.error_mode == "abort":
                    return PipelineResult(success=False, data=current_data, errors=errors, skipped=skipped)
        
        return PipelineResult(success=len(errors) == 0, data=current_data, errors=errors, skipped=skipped)


if __name__ == "__main__":
    pipeline = Pipeline()
    result = pipeline.execute({"test": "data"})
    print(result)
