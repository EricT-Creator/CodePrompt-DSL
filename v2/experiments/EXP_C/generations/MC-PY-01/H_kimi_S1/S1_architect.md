# MC-PY-01: Plugin-based Data Pipeline — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Pipeline Class Architecture

### 1.1 Class Hierarchy

```
Pipeline (Orchestrator)
├── plugins: list[PluginInterface]
├── conditions: dict[str, Callable]
└── execute(data) -> Result

PluginInterface (Protocol)
├── name: str
├── transform(data) -> Any
└── condition: str | None
```

### 1.2 Pipeline State

```python
from dataclasses import dataclass, field
from typing import Any, Protocol, Callable

class PluginInterface(Protocol):
    name: str
    
    def transform(self, data: Any) -> Any:
        ...

@dataclass
class Pipeline:
    plugins: list[Any] = field(default_factory=list)
    conditions: dict[str, Callable[[Any], bool]] = field(default_factory=dict)
    
    def register(self, plugin: Any, condition: str = None):
        """Register a plugin with optional condition key"""
        self.plugins.append((plugin, condition))
    
    def execute(self, data: Any) -> PipelineResult:
        """Execute all plugins in sequence"""
        ...
```

---

## 2. Plugin Loading Mechanism (exec flow)

### 2.1 Plugin File Format

```python
# plugin_example.py
name = "UpperCasePlugin"

def transform(data: str) -> str:
    return data.upper()

condition = "is_string"  # Optional: only run if condition met
```

### 2.2 exec() Loading Flow

```python
def load_plugin(file_path: str) -> Any:
    """Load plugin using exec()"""
    plugin_namespace = {}
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Execute in isolated namespace
    exec(source, plugin_namespace)
    
    # Create plugin instance from namespace
    class DynamicPlugin:
        def __init__(self, ns):
            self.name = ns.get('name', 'unnamed')
            self.transform = ns.get('transform', lambda x: x)
            self.condition = ns.get('condition')
    
    return DynamicPlugin(plugin_namespace)
```

### 2.3 Loading Multiple Plugins

```python
def load_plugins_from_directory(directory: str) -> list[Any]:
    """Load all .py files from directory as plugins"""
    plugins = []
    
    for file_path in Path(directory).glob('*.py'):
        try:
            plugin = load_plugin(str(file_path))
            plugins.append(plugin)
        except Exception as e:
            print(f"Failed to load {file_path}: {e}")
    
    return plugins
```

---

## 3. Protocol Interface Definition

### 3.1 Protocol Definition

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class TransformPlugin(Protocol):
    """Protocol for transform plugins"""
    name: str
    
    def transform(self, data: Any) -> Any:
        """Transform input data and return result"""
        ...

# Alternative: without @runtime_checkable for static type checking only
class TransformPlugin(Protocol):
    name: str
    def transform(self, data: Any) -> Any: ...
```

### 3.2 Type Checking

```python
def validate_plugin(plugin: Any) -> bool:
    """Check if object conforms to TransformPlugin protocol"""
    return (
        hasattr(plugin, 'name') and
        hasattr(plugin, 'transform') and
        callable(plugin.transform)
    )
```

---

## 4. Conditional Branch Design

### 4.1 Condition Registration

```python
# Register conditions
pipeline.register_condition("is_string", lambda data: isinstance(data, str))
pipeline.register_condition("is_positive", lambda data: isinstance(data, (int, float)) and data > 0)
pipeline.register_condition("is_list", lambda data: isinstance(data, list))
```

### 4.2 Conditional Execution

```python
@dataclass
class PipelineResult:
    success: bool
    data: Any
    executed_plugins: list[str]
    errors: list[str]

def execute(self, data: Any) -> PipelineResult:
    executed = []
    errors = []
    current_data = data
    
    for plugin, condition_key in self.plugins:
        # Check condition
        if condition_key:
            condition_fn = self.conditions.get(condition_key)
            if condition_fn and not condition_fn(current_data):
                continue  # Skip this plugin
        
        # Execute with error isolation
        try:
            current_data = plugin.transform(current_data)
            executed.append(plugin.name)
        except Exception as e:
            errors.append(f"{plugin.name}: {str(e)}")
            # Continue with next plugin (error isolation)
    
    return PipelineResult(
        success=len(errors) == 0,
        data=current_data,
        executed_plugins=executed,
        errors=errors
    )
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]PY310` | Python 3.10+ features (match, better typing) |
| `[D]STDLIB_ONLY` | No external dependencies |
| `[!D]NO_IMPORTLIB` | Uses `exec()` instead of importlib |
| `[PLUGIN]EXEC` | `exec(source, namespace)` for plugin loading |
| `[!D]NO_ABC` | Uses Protocol instead of ABC |
| `[IFACE]PROTOCOL` | typing.Protocol for interface definition |
| `[TYPE]FULL_HINTS` | Full type annotations throughout |
| `[ERR]ISOLATE` | Try/except per plugin, continues on error |
| `[O]CLASS` | Pipeline implemented as class |
| `[FILE]SINGLE` | Single file implementation |

---

## 6. Error Isolation Strategy

```python
def execute_isolated(self, data: Any) -> PipelineResult:
    """Execute plugins with full error isolation"""
    results = []
    
    for plugin, condition in self.plugins:
        try:
            result = plugin.transform(data)
            results.append({"plugin": plugin.name, "status": "success", "result": result})
            data = result  # Pass result to next plugin
        except Exception as e:
            results.append({"plugin": plugin.name, "status": "error", "error": str(e)})
            # Continue with original data
    
    return PipelineResult(...)
```

---

## 7. File Structure

```
MC-PY-01/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── pipeline.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
