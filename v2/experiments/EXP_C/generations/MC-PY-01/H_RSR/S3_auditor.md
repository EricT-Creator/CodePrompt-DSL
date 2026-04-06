## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS — All imports are Python 3.10 stdlib (`json`, `time`, `traceback`, `dataclasses`, `typing`, `sys`); no third-party packages. (Note: `importlib.util` is also stdlib but violates C2.)
- C2 [!D]NO_IMPORTLIB [PLUGIN]EXEC: FAIL — `import importlib.util` present at line 3795, violating `[!D]NO_IMPORTLIB`. The actual plugin loading correctly uses `exec(source_code, namespace)` per `[PLUGIN]EXEC`, but the unused `importlib.util` import must be removed.
- C3 [!D]NO_ABC [IFACE]PROTOCOL: PASS — No `abc.ABC` or `abc.ABCMeta` imported; interface defined via `@runtime_checkable class TransformPlugin(Protocol)` using structural typing.
- C4 [TYPE]FULL_HINTS: PASS — All functions and methods have full type annotations for parameters and return values throughout the file.
- C5 [ERR]ISOLATE: PASS — `Pipeline.run()` wraps each plugin execution in try/except, records the error via `context.add_error()`, appends a `PluginExecResult(status="failed")`, and continues to the next plugin without aborting the pipeline.
- C6 [O]CLASS [FILE]SINGLE: PASS — Code organized in classes (`PluginError`, `PipelineContext`, `PluginExecResult`, `PipelineResult`, `TransformPlugin`, `PluginRegistry`, `PluginLoader`, `Pipeline`); all in a single file.

## Functionality Assessment (0-5)
Score: 4 — Complete plugin-based data pipeline with exec()-based dynamic loading, Protocol-based structural typing for plugin interface, error isolation per plugin, registration/discovery system, and demonstration with three example plugins. Minor issues: `isinstance(obj, TransformPlugin)` with `@runtime_checkable` only checks method existence at the class level (not signatures), and the unused `importlib.util` import suggests incomplete refactoring.

## Corrected Code
```py
"""
Plugin-based Data Pipeline with exec() Loading

This module implements a plugin system for data processing pipelines,
using exec() for dynamic plugin loading and Protocol for interface definition.
"""

import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Protocol, runtime_checkable
import sys

# ============================================================================
# Error Classes
# ============================================================================

@dataclass
class PluginError:
    """Represents an error that occurred during plugin execution."""
    plugin_name: str
    error_message: str
    timestamp: float
    traceback: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plugin_name": self.plugin_name,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "traceback": self.traceback
        }

# ============================================================================
# Core Data Structures
# ============================================================================

@dataclass
class PipelineContext:
    """Mutable data container that flows through all plugins."""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[PluginError] = field(default_factory=list)
    
    def add_error(self, plugin_name: str, error_message: str, tb: Optional[str] = None) -> None:
        """Add an error to the context."""
        self.errors.append(PluginError(
            plugin_name=plugin_name,
            error_message=error_message,
            timestamp=time.time(),
            traceback=tb
        ))

@dataclass
class PluginExecResult:
    """Result of a single plugin execution."""
    plugin_name: str
    status: str  # "success", "skipped", "failed"
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plugin_name": self.plugin_name,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms
        }

@dataclass
class PipelineResult:
    """Result of a complete pipeline execution."""
    success: bool
    context: PipelineContext
    plugin_results: List[PluginExecResult]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "context": {
                "data": self.context.data,
                "metadata": self.context.metadata,
                "error_count": len(self.context.errors),
                "errors": [err.to_dict() for err in self.context.errors]
            },
            "plugin_results": [res.to_dict() for res in self.plugin_results],
            "total_plugins": len(self.plugin_results),
            "successful_plugins": sum(1 for res in self.plugin_results if res.status == "success"),
            "failed_plugins": sum(1 for res in self.plugin_results if res.status == "failed"),
            "skipped_plugins": sum(1 for res in self.plugin_results if res.status == "skipped")
        }

# ============================================================================
# Plugin Protocol
# ============================================================================

@runtime_checkable
class TransformPlugin(Protocol):
    """Protocol defining the interface for data transformation plugins."""
    
    @property
    def name(self) -> str:
        """Name of the plugin."""
        ...
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        """
        Transform data in the context.
        
        Args:
            context: The pipeline context containing data to transform
            
        Returns:
            Modified pipeline context
        """
        ...
    
    def should_run(self, context: PipelineContext) -> bool:
        """
        Determine if the plugin should execute.
        
        Args:
            context: The pipeline context to check
            
        Returns:
            True if plugin should run, False to skip
        """
        ...

# ============================================================================
# Plugin Registry
# ============================================================================

class PluginRegistry:
    """Manages plugin classes discovered and registered in the pipeline."""
    
    def __init__(self) -> None:
        self._plugins: List[Type[TransformPlugin]] = []
    
    def register(self, plugin_class: Type[TransformPlugin]) -> None:
        """Register a plugin class."""
        if not isinstance(plugin_class, type):
            raise TypeError(f"Expected a class, got {type(plugin_class)}")
        
        # Verify the class implements the protocol
        if not hasattr(plugin_class, 'name'):
            raise ValueError(f"Plugin class {plugin_class.__name__} missing 'name' property")
        
        if not hasattr(plugin_class, 'transform'):
            raise ValueError(f"Plugin class {plugin_class.__name__} missing 'transform' method")
        
        self._plugins.append(plugin_class)
    
    def get_plugins(self) -> List[Type[TransformPlugin]]:
        """Get all registered plugin classes."""
        return self._plugins.copy()
    
    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()

# ============================================================================
# Plugin Loader
# ============================================================================

class PluginLoader:
    """Loads plugin modules using exec() for dynamic plugin discovery."""
    
    def __init__(self) -> None:
        self._loaded_names: Dict[str, Dict[str, Any]] = {}
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load a plugin module from a file using exec().
        
        Args:
            file_path: Path to the plugin Python file
            
        Returns:
            Dictionary of names and objects from the plugin namespace
        """
        # Check if already loaded
        if file_path in self._loaded_names:
            return self._loaded_names[file_path]
        
        try:
            # Read the plugin source code
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Create a controlled namespace
            namespace: Dict[str, Any] = {
                "__name__": f"__plugin__{file_path}",
                "__file__": file_path,
                "__builtins__": __builtins__,
            }
            
            # Execute the plugin code in the namespace
            exec(source_code, namespace)
            
            # Store the loaded namespace
            self._loaded_names[file_path] = namespace
            
            return namespace
            
        except Exception as e:
            raise RuntimeError(f"Failed to load plugin from {file_path}: {e}")
    
    def discover_plugin_classes(self, namespace: Dict[str, Any]) -> List[Type[TransformPlugin]]:
        """
        Discover plugin classes in a namespace.
        
        Args:
            namespace: Dictionary of names and objects from exec()
            
        Returns:
            List of discovered plugin classes
        """
        plugin_classes: List[Type[TransformPlugin]] = []
        
        for name, obj in namespace.items():
            # Check if it's a class
            if not isinstance(obj, type):
                continue
            
            # Check if it implements the protocol (structural typing)
            if not isinstance(obj, TransformPlugin):
                continue
            
            plugin_classes.append(obj)
        
        return plugin_classes

# ============================================================================
# Pipeline Class
# ============================================================================

class Pipeline:
    """Main orchestrator for loading and executing plugin pipelines."""
    
    def __init__(self) -> None:
        self.registry = PluginRegistry()
        self.loader = PluginLoader()
        self.plugins: List[TransformPlugin] = []
    
    def load_plugin(self, file_path: str) -> None:
        """
        Load a plugin from a file and register discovered plugin classes.
        
        Args:
            file_path: Path to the plugin Python file
        """
        try:
            # Load plugin module
            namespace = self.loader.load_from_file(file_path)
            
            # Discover plugin classes
            plugin_classes = self.loader.discover_plugin_classes(namespace)
            
            # Register discovered classes
            for plugin_class in plugin_classes:
                self.registry.register(plugin_class)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load and register plugin from {file_path}: {e}")
    
    def register(self, plugin_class: Type[TransformPlugin]) -> None:
        """
        Manually register a plugin class.
        
        Args:
            plugin_class: The plugin class to register
        """
        self.registry.register(plugin_class)
    
    def initialize_plugins(self) -> None:
        """Initialize plugin instances from registered classes."""
        self.plugins.clear()
        
        for plugin_class in self.registry.get_plugins():
            try:
                plugin_instance = plugin_class()
                self.plugins.append(plugin_instance)
            except Exception as e:
                # Log error but continue (error isolation)
                print(f"Failed to initialize plugin {plugin_class.__name__}: {e}", file=sys.stderr)
    
    def run(self, input_data: Dict[str, Any]) -> PipelineResult:
        """
        Execute the pipeline with the given input data.
        
        Args:
            input_data: The data to process through the pipeline
            
        Returns:
            Pipeline execution result
        """
        # Initialize plugins if not already done
        if not self.plugins:
            self.initialize_plugins()
        
        # Create initial context
        context = PipelineContext(
            data=input_data.copy(),
            metadata={
                "start_time": time.time(),
                "pipeline_id": f"pipeline_{int(time.time())}",
                "plugin_count": len(self.plugins)
            }
        )
        
        plugin_results: List[PluginExecResult] = []
        all_successful = True
        
        # Execute plugins in registration order
        for plugin in self.plugins:
            start_time = time.time()
            
            try:
                # Check if plugin should run
                should_run = True
                if hasattr(plugin, 'should_run'):
                    should_run = plugin.should_run(context)
                
                if not should_run:
                    plugin_results.append(PluginExecResult(
                        plugin_name=plugin.name,
                        status="skipped",
                        duration_ms=(time.time() - start_time) * 1000
                    ))
                    continue
                
                # Execute plugin
                context = plugin.transform(context)
                
                plugin_results.append(PluginExecResult(
                    plugin_name=plugin.name,
                    status="success",
                    duration_ms=(time.time() - start_time) * 1000
                ))
                
            except Exception as e:
                # Capture error but continue execution (error isolation)
                error_msg = str(e)
                tb = traceback.format_exc()
                
                context.add_error(plugin.name, error_msg, tb)
                
                plugin_results.append(PluginExecResult(
                    plugin_name=plugin.name,
                    status="failed",
                    error=error_msg,
                    duration_ms=(time.time() - start_time) * 1000
                ))
                
                all_successful = False
        
        # Update context metadata
        context.metadata.update({
            "end_time": time.time(),
            "duration_seconds": time.time() - context.metadata["start_time"],
            "error_count": len(context.errors),
            "successful_plugins": sum(1 for res in plugin_results if res.status == "success")
        })
        
        return PipelineResult(
            success=all_successful,
            context=context,
            plugin_results=plugin_results
        )
    
    def reset(self) -> None:
        """Reset the pipeline to its initial state."""
        self.registry.clear()
        self.plugins.clear()
        self.loader._loaded_names.clear()

# ============================================================================
# Example Plugin Implementation (for demonstration)
# ============================================================================

class ExamplePlugin1:
    """Example plugin that adds a timestamp to the data."""
    
    @property
    def name(self) -> str:
        return "timestamp_adder"
    
    def should_run(self, context: PipelineContext) -> bool:
        # Always run this plugin
        return True
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        context.data["timestamp"] = time.time()
        context.data["pipeline_stage"] = "after_plugin1"
        return context

class ExamplePlugin2:
    """Example plugin that filters data based on a condition."""
    
    @property
    def name(self) -> str:
        return "data_filter"
    
    def should_run(self, context: PipelineContext) -> bool:
        # Only run if there's data to process
        return len(context.data) > 0
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        # Example: remove any entries with value None
        if "items" in context.data and isinstance(context.data["items"], list):
            context.data["items"] = [item for item in context.data["items"] if item is not None]
        
        context.data["pipeline_stage"] = "after_plugin2"
        return context

class ExamplePlugin3:
    """Example plugin that calculates statistics."""
    
    @property
    def name(self) -> str:
        return "statistics_calculator"
    
    def should_run(self, context: PipelineContext) -> bool:
        # Only run if there are items to analyze
        return "items" in context.data and isinstance(context.data["items"], list)
    
    def transform(self, context: PipelineContext) -> PipelineContext:
        items = context.data["items"]
        
        if items:
            context.data["statistics"] = {
                "count": len(items),
                "sum": sum(items) if all(isinstance(i, (int, float)) for i in items) else None,
                "average": sum(items) / len(items) if all(isinstance(i, (int, float)) for i in items) else None
            }
        
        context.data["pipeline_stage"] = "after_plugin3"
        return context

# ============================================================================
# Demonstration Function
# ============================================================================

def demonstrate_pipeline() -> None:
    """Demonstrate the pipeline with example plugins."""
    
    # Create pipeline
    pipeline = Pipeline()
    
    # Manually register example plugins
    pipeline.register(ExamplePlugin1)
    pipeline.register(ExamplePlugin2)
    pipeline.register(ExamplePlugin3)
    
    # Prepare input data
    input_data = {
        "items": [1, 2, 3, None, 5, 6],
        "source": "test_data"
    }
    
    print("Starting pipeline execution...")
    print(f"Input data: {input_data}")
    print("-" * 80)
    
    # Run pipeline
    result = pipeline.run(input_data)
    
    # Print results
    print(f"Pipeline success: {result.success}")
    print(f"Final data: {json.dumps(result.context.data, indent=2)}")
    
    print("\nPlugin Results:")
    for plugin_result in result.plugin_results:
        print(f"  {plugin_result.plugin_name}: {plugin_result.status} ({plugin_result.duration_ms:.2f} ms)")
    
    print("\nErrors:")
    for error in result.context.errors:
        print(f"  {error.plugin_name}: {error.error_message}")
    
    print(f"\nTotal duration: {result.context.metadata['duration_seconds']:.2f} seconds")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    demonstrate_pipeline()
```
