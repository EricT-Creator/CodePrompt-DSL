from typing import Protocol, Callable, Any, Optional, List, Dict
from pathlib import Path
import traceback
from dataclasses import dataclass
import sys


class TransformPlugin(Protocol):
    """Protocol for ETL transform plugins."""
    name: str
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class PluginError:
    """Error information for a failed plugin."""
    plugin_name: str
    error_type: str
    message: str
    traceback: str


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool
    data: Dict[str, Any]
    errors: List[PluginError]
    skipped: List[str]


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""
    plugin_dir: Optional[str] = None
    plugin_files: Optional[List[str]] = None
    abort_on_error: bool = False
    log_errors: bool = True


class Pipeline:
    """Plugin-based ETL data pipeline."""
    
    def __init__(self, config: PipelineConfig) -> None:
        """Initialize pipeline with configuration."""
        self.config = config
        self.plugins: List[tuple[TransformPlugin, Optional[Callable[[Dict[str, Any]], bool]]]] = []
        
    def load_plugin(self, file_path: str) -> None:
        """Load a single plugin file using exec()."""
        try:
            source = Path(file_path).read_text(encoding='utf-8')
            namespace: Dict[str, Any] = {}
            exec(source, namespace)
            
            plugin_class = self._find_plugin_class(namespace)
            if plugin_class:
                plugin_instance = plugin_class()
                self.register(plugin_instance)
            elif self.config.log_errors:
                print(f"No valid plugin class found in {file_path}", file=sys.stderr)
                
        except Exception as e:
            if self.config.log_errors:
                error_msg = f"Failed to load plugin from {file_path}: {e}"
                print(error_msg, file=sys.stderr)
    
    def load_plugins(self, directory: str) -> None:
        """Load all .py files from a directory."""
        plugin_dir = Path(directory)
        if not plugin_dir.is_dir():
            if self.config.log_errors:
                print(f"Directory {directory} does not exist", file=sys.stderr)
            return
            
        for file_path in sorted(plugin_dir.glob("*.py")):
            if file_path.name != "__init__.py":
                self.load_plugin(str(file_path))
    
    def _find_plugin_class(self, namespace: Dict[str, Any]) -> Optional[type]:
        """Find a class implementing TransformPlugin in namespace."""
        for obj in namespace.values():
            if isinstance(obj, type) and obj is not TransformPlugin:
                try:
                    if hasattr(obj, 'name') and hasattr(obj, 'transform'):
                        transform_method = obj.transform
                        if callable(transform_method):
                            return obj
                except Exception:
                    continue
        return None
    
    def register(self, plugin: TransformPlugin, condition: Optional[Callable[[Dict[str, Any]], bool]] = None) -> None:
        """Register a plugin with optional condition."""
        self.plugins.append((plugin, condition))
    
    def execute(self, data: Dict[str, Any]) -> PipelineResult:
        """Execute all registered plugins on the data."""
        current_data = data.copy()
        errors: List[PluginError] = []
        skipped: List[str] = []
        
        for plugin, condition in self.plugins:
            plugin_name = plugin.name
            
            if condition is not None and not condition(current_data):
                skipped.append(plugin_name)
                continue
            
            try:
                current_data = plugin.transform(current_data)
            except Exception as e:
                error = PluginError(
                    plugin_name=plugin_name,
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback=traceback.format_exc()
                )
                errors.append(error)
                
                if self.config.abort_on_error:
                    break
        
        success = len(errors) == 0
        return PipelineResult(
            success=success,
            data=current_data,
            errors=errors,
            skipped=skipped
        )