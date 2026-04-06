from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable
from dataclasses import dataclass, field


# ─── Protocol Interface ───

@runtime_checkable
class Plugin(Protocol):
    """Protocol defining the plugin interface."""

    name: str

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        ...

    def setup(self) -> None:
        ...

    def teardown(self) -> None:
        ...


# ─── Pipeline Context ───

@dataclass
class PipelineContext:
    """Shared context passed through pipeline execution."""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)


# ─── Condition type ───

Condition = Callable[[PipelineContext], bool]


# ─── Pipeline ───

class Pipeline:
    """ETL Pipeline with plugin-based transform stages."""

    def __init__(self) -> None:
        self._plugins: list[Plugin] = []
        self._conditions: dict[int, Condition] = {}

    def add_plugin(
        self,
        plugin: Plugin,
        condition: Condition | None = None,
    ) -> Pipeline:
        """Add a plugin to the pipeline with optional conditional execution."""
        self._plugins.append(plugin)
        if condition is not None:
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
                # Setup
                if hasattr(plugin, "setup"):
                    plugin.setup()

                # Execute plugin with error isolation
                context = self._execute_plugin(plugin, context)

                # Teardown
                if hasattr(plugin, "teardown"):
                    plugin.teardown()
            except Exception as e:
                context.errors.append({
                    "plugin": plugin.name,
                    "error": str(e),
                    "stage": idx,
                })

        return context

    def _execute_plugin(self, plugin: Plugin, context: PipelineContext) -> PipelineContext:
        """Execute single plugin and return updated context."""
        result = plugin.transform(context.data, context.metadata)
        context.data = result
        return context

    def list_plugins(self) -> list[str]:
        """List all plugin names in execution order."""
        return [p.name for p in self._plugins]


# ─── Plugin Registry ───

class PluginRegistry:
    """Registry for loaded plugins."""

    def __init__(self) -> None:
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


# ─── Plugin Loading via exec() ───

def load_plugin_from_file(file_path: str, registry: PluginRegistry) -> bool:
    """Load a plugin from Python file using exec()."""
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    namespace: dict[str, Any] = {
        "__name__": f"plugin_{Path(file_path).stem}",
        "__file__": file_path,
    }

    try:
        exec(source, namespace)
    except Exception:
        return False

    for name, obj in namespace.items():
        if (
            isinstance(obj, type)
            and name != "Plugin"
            and hasattr(obj, "transform")
            and hasattr(obj, "name")
        ):
            registry.register(name, obj)
            return True

    return False


def load_plugins_from_directory(directory: str, registry: PluginRegistry) -> list[str]:
    """Load all plugins from a directory."""
    loaded: list[str] = []
    if not os.path.isdir(directory):
        return loaded
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".py") and not filename.startswith("_"):
            file_path = os.path.join(directory, filename)
            if load_plugin_from_file(file_path, registry):
                loaded.append(filename[:-3])
    return loaded


# ─── Plugin Instantiation ───

def instantiate_plugin(plugin_class: type, config: dict[str, Any] | None = None) -> Plugin:
    """Create plugin instance with optional configuration."""
    if config:
        return plugin_class(**config)
    return plugin_class()


# ─── Condition Factories ───

def field_exists(field_name: str) -> Condition:
    """Create condition that checks if field exists in data."""
    def check(context: PipelineContext) -> bool:
        return field_name in context.data
    return check


def field_equals(field_name: str, value: Any) -> Condition:
    """Create condition that checks if field equals value."""
    def check(context: PipelineContext) -> bool:
        return context.data.get(field_name) == value
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


# ─── Built-in Plugins ───

class UpperCasePlugin:
    """Plugin that converts all string values to uppercase."""
    name: str = "upper_case"

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = v.upper()
            else:
                result[k] = v
        return result

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


class FilterKeysPlugin:
    """Plugin that filters data to only include specified keys."""
    name: str = "filter_keys"

    def __init__(self, keys: list[str] | None = None) -> None:
        self.keys: list[str] = keys or []

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        if not self.keys:
            return data
        return {k: v for k, v in data.items() if k in self.keys}

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


class ValidatePlugin:
    """Plugin that validates required fields exist in data."""
    name: str = "validate"

    def __init__(self, required_fields: list[str] | None = None) -> None:
        self.required_fields: list[str] = required_fields or []

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        for f in self.required_fields:
            if f not in data:
                raise ValueError(f"Required field '{f}' missing")
        return data

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


class AddTimestampPlugin:
    """Plugin that adds a processing timestamp to data."""
    name: str = "add_timestamp"

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone
        data["_processed_at"] = datetime.now(timezone.utc).isoformat()
        return data

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


class RenameKeysPlugin:
    """Plugin that renames keys in data."""
    name: str = "rename_keys"

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping: dict[str, str] = mapping or {}

    def transform(self, data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in data.items():
            new_key = self.mapping.get(k, k)
            result[new_key] = v
        return result

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass


# ─── Demo / Main ───

if __name__ == "__main__":
    # Create registry and register built-in plugins
    registry = PluginRegistry()
    registry.register("UpperCasePlugin", UpperCasePlugin)
    registry.register("FilterKeysPlugin", FilterKeysPlugin)
    registry.register("ValidatePlugin", ValidatePlugin)
    registry.register("AddTimestampPlugin", AddTimestampPlugin)
    registry.register("RenameKeysPlugin", RenameKeysPlugin)

    # Build pipeline
    pipeline = Pipeline()
    pipeline.add_plugin(
        ValidatePlugin(required_fields=["name", "email"]),
    )
    pipeline.add_plugin(
        UpperCasePlugin(),
        condition=field_exists("name"),
    )
    pipeline.add_plugin(
        FilterKeysPlugin(keys=["name", "email"]),
        condition=field_equals("type", "user"),
    )
    pipeline.add_plugin(AddTimestampPlugin())

    # Execute
    result = pipeline.execute(initial_data={
        "name": "Alice",
        "email": "alice@example.com",
        "type": "user",
        "extra": "data",
    })

    print("Result data:", result.data)
    print("Errors:", result.errors)
    print("Plugins:", pipeline.list_plugins())
