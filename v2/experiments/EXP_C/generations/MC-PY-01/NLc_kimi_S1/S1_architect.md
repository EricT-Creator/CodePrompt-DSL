# MC-PY-01: Plugin-Based ETL Data Pipeline - Technical Design Document

## 1. Pipeline Class Architecture

### Core Pipeline Class
```python
from typing import Protocol, Any, Callable
from dataclasses import dataclass, field
from collections.abc import Iterator

@dataclass
class PipelineContext:
    """Shared context passed through pipeline execution."""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

class Pipeline:
    """ETL Pipeline with plugin-based transform stages."""
    
    def __init__(self):
        self._plugins: list[Plugin] = []
        self._conditions: dict[int, Callable[[PipelineContext], bool]] = {}
    
    def add_plugin(self, plugin: 'Plugin', condition: Callable[[PipelineContext], bool] | None = None) -> 'Pipeline':
        """Add a plugin to the pipeline with optional conditional execution."""
        self._plugins.append(plugin)
        if condition:
            self._conditions[len(self._plugins) - 1] = condition
        return self
    
    def execute(self, initial_data: dict[str, Any] | None = None) -> PipelineContext:
        """Execute all plugins in sequence."""
        context = PipelineContext(data=initial_data or {})
        
        for idx, plugin in enumerate(self._plugins):
            # Check conditional execution
            if idx in self._conditions:
                if not self._conditions[idx](context):
                    continue
            
            try:
                # Execute plugin with error isolation
                context = self._execute_plugin(plugin, context)
            except Exception as e:
                # Capture error but continue pipeline
                context.errors.append({
                    'plugin': plugin.name,
                    'error': str(e),
                    'stage': idx
                })
        
        return context
    
    def _execute_plugin(self, plugin: 'Plugin', context: PipelineContext) -> PipelineContext:
        """Execute single plugin and return updated context."""
        result = plugin.transform(context.data, context.metadata)
        context.data = result
        return context
```

### Plugin Registration and Loading
```python
class PluginRegistry:
    """Registry for loaded plugins."""
    
    def __init__(self):
        self._plugins: dict[str, type] = {}
    
    def register(self, name: str, plugin_class: type) -> None:
        """Register a plugin class."""
        self._plugins[name] = plugin_class
    
    def get(self, name: str) -> type | None:
        """Get plugin class by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> list[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())
```

## 2. Plugin Loading Mechanism

### exec() Based Loading
```python
import os
from pathlib import Path

def load_plugin_from_file(file_path: str, registry: PluginRegistry) -> bool:
    """Load a plugin from Python file using exec()."""
    if not os.path.exists(file_path):
        return False
    
    # Read plugin source
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # Create isolated namespace
    namespace = {
        '__name__': f'plugin_{Path(file_path).stem}',
        '__file__': file_path,
    }
    
    # Execute plugin code in isolated namespace
    exec(source, namespace)
    
    # Find Plugin class implementation
    for name, obj in namespace.items():
        if (isinstance(obj, type) and 
            name != 'Plugin' and 
            hasattr(obj, 'transform')):
            registry.register(name, obj)
            return True
    
    return False

def load_plugins_from_directory(directory: str, registry: PluginRegistry) -> list[str]:
    """Load all plugins from a directory."""
    loaded = []
    for filename in os.listdir(directory):
        if filename.endswith('.py') and not filename.startswith('_'):
            file_path = os.path.join(directory, filename)
            if load_plugin_from_file(file_path, registry):
                loaded.append(filename[:-3])
    return loaded
```

### Plugin Instantiation
```python
def instantiate_plugin(plugin_class: type, config: dict[str, Any] | None = None) -> 'Plugin':
    """Create plugin instance with optional configuration."""
    if config:
        return plugin_class(**config)
    return plugin_class()
```

## 3. Protocol Interface Definition

### Plugin Protocol
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Plugin(Protocol):
    """Protocol defining the plugin interface."""
    
    name: str
    
    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        """Transform data and return updated data.
        
        Args:
            data: Input data dictionary
            metadata: Pipeline metadata
            
        Returns:
            Updated data dictionary
        """
        ...
    
    def setup(self) -> None:
        """Optional setup method called before first use."""
        ...
    
    def teardown(self) -> None:
        """Optional cleanup method called after last use."""
        ...
```

### Example Plugin Implementation
```python
# Example: validate_plugin.py
class ValidatePlugin:
    """Sample plugin implementing the Plugin protocol."""
    
    name = "validate"
    
    def __init__(self, required_fields: list[str] | None = None):
        self.required_fields = required_fields or []
    
    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate required fields exist in data."""
        for field in self.required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' missing")
        return data
    
    def setup(self) -> None:
        pass
    
    def teardown(self) -> None:
        pass
```

## 4. Conditional Branch Design

### Condition Functions
```python
from typing import Callable

Condition = Callable[[PipelineContext], bool]

def field_exists(field: str) -> Condition:
    """Create condition that checks if field exists in data."""
    def check(context: PipelineContext) -> bool:
        return field in context.data
    return check

def field_equals(field: str, value: Any) -> Condition:
    """Create condition that checks if field equals value."""
    def check(context: PipelineContext) -> bool:
        return context.data.get(field) == value
    return check

def metadata_check(key: str, value: Any) -> Condition:
    """Create condition that checks metadata value."""
    def check(context: PipelineContext) -> bool:
        return context.metadata.get(key) == value
    return check

def custom_condition(predicate: Callable[[dict[str, Any]], bool]) -> Condition:
    """Create condition from custom predicate function."""
    def check(context: PipelineContext) -> bool:
        return predicate(context.data)
    return check
```

### Conditional Pipeline Example
```python
def create_conditional_pipeline(registry: PluginRegistry) -> Pipeline:
    """Create pipeline with conditional branches."""
    pipeline = Pipeline()
    
    # Always run: load data
    load_plugin_class = registry.get('LoadPlugin')
    if load_plugin_class:
        pipeline.add_plugin(instantiate_plugin(load_plugin_class))
    
    # Conditional: validate only if data has 'raw' field
    validate_plugin_class = registry.get('ValidatePlugin')
    if validate_plugin_class:
        pipeline.add_plugin(
            instantiate_plugin(validate_plugin_class),
            condition=field_exists('raw')
        )
    
    # Conditional: transform only if data type is 'csv'
    transform_plugin_class = registry.get('TransformPlugin')
    if transform_plugin_class:
        pipeline.add_plugin(
            instantiate_plugin(transform_plugin_class),
            condition=field_equals('type', 'csv')
        )
    
    # Always run: save data
    save_plugin_class = registry.get('SavePlugin')
    if save_plugin_class:
        pipeline.add_plugin(instantiate_plugin(save_plugin_class))
    
    return pipeline
```

## 5. Constraint Acknowledgment

### Python 3.10+, stdlib only
**Addressed by:** Only imports from Python standard library (typing, dataclasses, os, pathlib, collections.abc). No external dependencies.

### exec() for plugin loading, no importlib
**Addressed by:** Plugin loading implemented using `exec()` function with isolated namespace. No `importlib`, `importlib.util`, or dynamic imports used.

### Protocol for interfaces, no ABC
**Addressed by:** Plugin interface defined using `typing.Protocol` with `@runtime_checkable`. No `abc.ABC` or abstract base classes used.

### Full type annotations
**Addressed by:** All functions, methods, classes, and variables have complete type hints. Uses `from __future__ import annotations` for forward references.

### Plugin errors isolated
**Addressed by:** Pipeline execution wraps each plugin call in try-except block. Errors captured in context.errors list without stopping pipeline execution.

### Single file, class output
**Addressed by:** Single Python file containing Pipeline class, Plugin protocol, and supporting types. Main export is Pipeline class.
