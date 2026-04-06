# MC-PY-01: Plugin-Based ETL Data Pipeline - Technical Design

## Overview

This document outlines the technical design for a plugin-based ETL data pipeline with runtime plugin loading via exec(), Protocol-based interfaces, conditional branches, and error isolation.

## 1. Pipeline Class Architecture

### Class Structure

```python
from typing import Protocol, Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

class Pipeline:
    """
    ETL Pipeline that loads and executes plugins at runtime.
    
    Responsibilities:
    - Plugin discovery and loading via exec()
    - Sequential execution with conditional branches
    - Error isolation between plugins
    - Data flow management between stages
    """
    
    def __init__(self):
        self._plugins: List[PluginWrapper] = []
        self._context: Dict[str, Any] = {}  # Shared pipeline context
    
    def load_plugin(self, plugin_path: Path) -> None:
        """Load a plugin from file using exec()."""
        pass
    
    def add_stage(
        self,
        plugin_name: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> None:
        """Add a plugin to the pipeline with optional condition."""
        pass
    
    def execute(self, initial_data: Any) -> PipelineResult:
        """Execute the pipeline and return results."""
        pass
```

### Plugin Wrapper

```python
@dataclass
class PluginWrapper:
    """Wrapper for loaded plugin with metadata."""
    name: str
    instance: Any  # Object implementing TransformProtocol
    condition: Optional[Callable[[Dict[str, Any]], bool]]
    error_count: int = 0
```

### Pipeline Result

```python
@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    data: Any
    executed_stages: List[str]
    skipped_stages: List[str]
    errors: List[PluginError]
    context: Dict[str, Any]

@dataclass
class PluginError:
    """Error information from a failed plugin."""
    plugin_name: str
    stage_index: int
    error_type: str
    error_message: str
```

## 2. Plugin Loading Mechanism

### exec() Loading Flow

```python
def load_plugin(self, plugin_path: Path) -> None:
    """
    Load plugin by reading file and executing with exec().
    
    Steps:
    1. Read plugin file content
    2. Create isolated namespace
    3. Execute plugin code with exec()
    4. Extract plugin class/instance
    5. Validate against TransformProtocol
    6. Store for pipeline use
    """
    # Read plugin file
    plugin_code = plugin_path.read_text()
    
    # Create namespace with restricted builtins
    namespace = {
        '__builtins__': {
            'print': print,
            'len': len,
            'range': range,
            'dict': dict,
            'list': list,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'Exception': Exception,
            'TypeError': TypeError,
            'ValueError': ValueError,
        }
    }
    
    # Execute plugin code
    exec(plugin_code, namespace)
    
    # Find plugin class (convention: class ending with 'Plugin')
    plugin_class = None
    for name, obj in namespace.items():
        if (isinstance(obj, type) and 
            name.endswith('Plugin') and
            hasattr(obj, 'transform')):
            plugin_class = obj
            break
    
    if not plugin_class:
        raise ValueError(f"No plugin class found in {plugin_path}")
    
    # Store plugin factory
    self._plugin_registry[plugin_path.stem] = plugin_class
```

### Plugin Discovery

```python
def load_plugins_from_directory(self, directory: Path) -> None:
    """Load all plugins from a directory."""
    for plugin_file in directory.glob("*.py"):
        try:
            self.load_plugin(plugin_file)
        except Exception as e:
            # Log error but continue loading other plugins
            print(f"Failed to load {plugin_file}: {e}")
```

## 3. Protocol Interface Definition

### TransformProtocol

```python
from typing import Protocol, Any, Dict, runtime_checkable

@runtime_checkable
class TransformProtocol(Protocol):
    """
    Protocol defining the transform interface for ETL plugins.
    
    All plugins must implement this interface to be usable in the pipeline.
    """
    
    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Transform input data and return result.
        
        Args:
            data: Input data from previous stage or initial input
            context: Shared pipeline context (read/write allowed)
        
        Returns:
            Transformed data for next stage
        
        Raises:
            TransformError: If transformation fails
        """
        ...
    
    def get_name(self) -> str:
        """Return plugin name for logging/debugging."""
        ...
```

### Example Plugin Implementation

```python
# Example plugin file: uppercase_plugin.py

class UppercasePlugin:
    """Plugin that converts string data to uppercase."""
    
    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        if isinstance(data, str):
            return data.upper()
        return data
    
    def get_name(self) -> str:
        return "UppercasePlugin"
```

## 4. Conditional Branch Design

### Condition Functions

```python
class Pipeline:
    def add_stage(
        self,
        plugin_name: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> None:
        """
        Add a stage to the pipeline.
        
        Args:
            plugin_name: Name of loaded plugin to execute
            condition: Optional function that receives context and returns
                      True if stage should execute, False to skip
        """
        if plugin_name not in self._plugin_registry:
            raise ValueError(f"Plugin '{plugin_name}' not loaded")
        
        plugin_class = self._plugin_registry[plugin_name]
        wrapper = PluginWrapper(
            name=plugin_name,
            instance=plugin_class(),
            condition=condition
        )
        self._plugins.append(wrapper)
```

### Conditional Execution Flow

```python
def execute(self, initial_data: Any) -> PipelineResult:
    """Execute pipeline with conditional branching."""
    data = initial_data
    executed = []
    skipped = []
    errors = []
    
    for index, wrapper in enumerate(self._plugins):
        # Check condition
        if wrapper.condition and not wrapper.condition(self._context):
            skipped.append(wrapper.name)
            continue
        
        # Execute with error isolation
        try:
            data = wrapper.instance.transform(data, self._context)
            executed.append(wrapper.name)
        except Exception as e:
            # Isolate error - don't crash pipeline
            errors.append(PluginError(
                plugin_name=wrapper.name,
                stage_index=index,
                error_type=type(e).__name__,
                error_message=str(e)
            ))
            # Continue with original data
    
    return PipelineResult(
        success=len(errors) == 0,
        data=data,
        executed_stages=executed,
        skipped_stages=skipped,
        errors=errors,
        context=self._context
    )
```

### Usage Examples

```python
# Create pipeline
pipeline = Pipeline()
pipeline.load_plugin(Path("plugins/uppercase_plugin.py"))
pipeline.load_plugin(Path("plugins/filter_plugin.py"))
pipeline.load_plugin(Path("plugins/enrich_plugin.py"))

# Add stages with conditions
pipeline.add_stage("UppercasePlugin")  # Always runs

pipeline.add_stage(
    "FilterPlugin",
    condition=lambda ctx: ctx.get("filter_enabled", False)
)  # Only runs if filter_enabled is True

pipeline.add_stage(
    "EnrichPlugin",
    condition=lambda ctx: ctx.get("data_source") == "api"
)  # Only runs for API data source

# Execute
result = pipeline.execute("hello world")
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python 3.10+, standard library only** | No external dependencies; use typing, dataclasses, pathlib |
| **exec() for plugin loading** | Read plugin file, execute with restricted namespace, extract class |
| **typing.Protocol for interface** | Define `TransformProtocol` with `@runtime_checkable` for validation |
| **Full type annotations** | All public methods typed with Any, Dict, List, Optional, Callable |
| **Error isolation** | try/except around each plugin.transform() call; errors collected, pipeline continues |
| **Single Python file** | Pipeline class as main output with all supporting classes |

## Summary

This design implements a flexible ETL pipeline using Python's Protocol for interface definition and exec() for runtime plugin loading. The Protocol approach avoids ABC inheritance while still enabling type checking. Error isolation ensures one plugin failure doesn't crash the entire pipeline. Conditional branches allow dynamic execution based on pipeline context, enabling complex data flows without hardcoded logic.
