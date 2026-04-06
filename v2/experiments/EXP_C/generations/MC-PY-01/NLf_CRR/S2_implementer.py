"""Plugin-Based ETL Data Pipeline — exec() loading, Protocol interfaces, error isolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

# ─── Exceptions ───────────────────────────────────────────────────────────────

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class PluginLoadError(PipelineError):
    """Raised when a plugin cannot be loaded."""
    pass


# ─── Protocol Interface ──────────────────────────────────────────────────────

@runtime_checkable
class TransformProtocol(Protocol):
    """Protocol defining the transform interface for ETL plugins."""

    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        """Transform input data and return result."""
        ...

    def get_name(self) -> str:
        """Return plugin name for logging/debugging."""
        ...


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class PluginError:
    """Error information from a failed plugin."""
    plugin_name: str
    stage_index: int
    error_type: str
    error_message: str


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
class PluginWrapper:
    """Wrapper for loaded plugin with metadata."""
    name: str
    instance: Any
    condition: Optional[Callable[[Dict[str, Any]], bool]]
    error_count: int = 0


# ─── Pipeline Class ──────────────────────────────────────────────────────────

class Pipeline:
    """
    ETL Pipeline that loads and executes plugins at runtime.

    Responsibilities:
    - Plugin discovery and loading via exec()
    - Sequential execution with conditional branches
    - Error isolation between plugins
    - Data flow management between stages
    """

    def __init__(self) -> None:
        self._plugin_registry: Dict[str, type] = {}
        self._stages: List[PluginWrapper] = []
        self._context: Dict[str, Any] = {}

    @property
    def context(self) -> Dict[str, Any]:
        """Access the shared pipeline context."""
        return self._context

    @context.setter
    def context(self, value: Dict[str, Any]) -> None:
        self._context = value

    def load_plugin(self, plugin_path: Path) -> str:
        """
        Load a plugin from file using exec().

        Args:
            plugin_path: Path to the plugin Python file.

        Returns:
            Name of the loaded plugin class.

        Raises:
            PluginLoadError: If the plugin cannot be loaded or is invalid.
        """
        if not plugin_path.exists():
            raise PluginLoadError(f"Plugin file not found: {plugin_path}")

        try:
            plugin_code = plugin_path.read_text(encoding="utf-8")
        except OSError as e:
            raise PluginLoadError(f"Cannot read plugin file {plugin_path}: {e}")

        namespace: Dict[str, Any] = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "dict": dict,
                "list": list,
                "tuple": tuple,
                "set": set,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "None": None,
                "True": True,
                "False": False,
                "isinstance": isinstance,
                "type": type,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "reversed": reversed,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "any": any,
                "all": all,
                "hasattr": hasattr,
                "getattr": getattr,
                "setattr": setattr,
                "Exception": Exception,
                "TypeError": TypeError,
                "ValueError": ValueError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "RuntimeError": RuntimeError,
                "StopIteration": StopIteration,
            }
        }

        try:
            exec(plugin_code, namespace)
        except Exception as e:
            raise PluginLoadError(f"Error executing plugin {plugin_path}: {e}")

        plugin_class: Optional[type] = None
        plugin_name: Optional[str] = None

        for name, obj in namespace.items():
            if name.startswith("_"):
                continue
            if isinstance(obj, type) and name.endswith("Plugin") and hasattr(obj, "transform"):
                plugin_class = obj
                plugin_name = name
                break

        if plugin_class is None or plugin_name is None:
            raise PluginLoadError(
                f"No valid plugin class found in {plugin_path}. "
                "Plugin class must end with 'Plugin' and have a 'transform' method."
            )

        self._plugin_registry[plugin_name] = plugin_class
        return plugin_name

    def load_plugins_from_directory(self, directory: Path) -> List[str]:
        """
        Load all plugins from a directory.

        Args:
            directory: Path to directory containing plugin .py files.

        Returns:
            List of successfully loaded plugin names.
        """
        loaded: List[str] = []
        if not directory.is_dir():
            return loaded

        for plugin_file in sorted(directory.glob("*.py")):
            try:
                name = self.load_plugin(plugin_file)
                loaded.append(name)
            except PluginLoadError:
                # Isolated: skip failed plugins, continue loading others
                pass

        return loaded

    def add_stage(
        self,
        plugin_name: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> None:
        """
        Add a plugin stage to the pipeline.

        Args:
            plugin_name: Name of a loaded plugin class.
            condition: Optional function; stage executes only if it returns True.

        Raises:
            ValueError: If the plugin is not loaded.
        """
        if plugin_name not in self._plugin_registry:
            raise ValueError(f"Plugin '{plugin_name}' not loaded. Available: {list(self._plugin_registry.keys())}")

        plugin_class = self._plugin_registry[plugin_name]
        try:
            instance = plugin_class()
        except Exception as e:
            raise ValueError(f"Cannot instantiate plugin '{plugin_name}': {e}")

        wrapper = PluginWrapper(
            name=plugin_name,
            instance=instance,
            condition=condition,
        )
        self._stages.append(wrapper)

    def execute(self, initial_data: Any) -> PipelineResult:
        """
        Execute the pipeline sequentially with error isolation.

        Args:
            initial_data: The initial data to feed into the first stage.

        Returns:
            PipelineResult with execution details.
        """
        data = initial_data
        executed: List[str] = []
        skipped: List[str] = []
        errors: List[PluginError] = []

        for index, wrapper in enumerate(self._stages):
            # Check condition
            if wrapper.condition is not None:
                try:
                    should_run = wrapper.condition(self._context)
                except Exception:
                    should_run = False

                if not should_run:
                    skipped.append(wrapper.name)
                    continue

            # Execute with error isolation
            try:
                result = wrapper.instance.transform(data, self._context)
                data = result
                executed.append(wrapper.name)
            except Exception as e:
                wrapper.error_count += 1
                errors.append(
                    PluginError(
                        plugin_name=wrapper.name,
                        stage_index=index,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                )
                # Continue with unchanged data — pipeline doesn't crash

        return PipelineResult(
            success=len(errors) == 0,
            data=data,
            executed_stages=executed,
            skipped_stages=skipped,
            errors=errors,
            context=dict(self._context),
        )

    def get_loaded_plugins(self) -> List[str]:
        """Return list of loaded plugin names."""
        return list(self._plugin_registry.keys())

    def get_stages(self) -> List[str]:
        """Return list of stage names in order."""
        return [w.name for w in self._stages]

    def clear_stages(self) -> None:
        """Remove all stages but keep loaded plugins."""
        self._stages.clear()

    def reset(self) -> None:
        """Reset pipeline completely."""
        self._plugin_registry.clear()
        self._stages.clear()
        self._context.clear()


# ─── Built-in Demo Plugins (for standalone testing) ──────────────────────────

class UppercasePlugin:
    """Plugin that converts string data to uppercase."""

    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        if isinstance(data, str):
            return data.upper()
        if isinstance(data, list):
            return [item.upper() if isinstance(item, str) else item for item in data]
        return data

    def get_name(self) -> str:
        return "UppercasePlugin"


class FilterEmptyPlugin:
    """Plugin that removes empty strings from a list."""

    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        if isinstance(data, list):
            return [item for item in data if item]
        return data

    def get_name(self) -> str:
        return "FilterEmptyPlugin"


class CountPlugin:
    """Plugin that stores a count in context and passes data through."""

    def transform(self, data: Any, context: Dict[str, Any]) -> Any:
        if isinstance(data, (list, tuple)):
            context["item_count"] = len(data)
        elif isinstance(data, str):
            context["char_count"] = len(data)
        return data

    def get_name(self) -> str:
        return "CountPlugin"


# ─── Standalone Demo ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = Pipeline()

    # Register built-in plugins directly
    pipeline._plugin_registry["UppercasePlugin"] = UppercasePlugin
    pipeline._plugin_registry["FilterEmptyPlugin"] = FilterEmptyPlugin
    pipeline._plugin_registry["CountPlugin"] = CountPlugin

    # Build pipeline with conditions
    pipeline.add_stage("FilterEmptyPlugin")
    pipeline.add_stage("UppercasePlugin")
    pipeline.add_stage(
        "CountPlugin",
        condition=lambda ctx: ctx.get("count_enabled", True),
    )

    # Execute
    test_data = ["hello", "", "world", "", "python", "pipeline"]
    result = pipeline.execute(test_data)

    print(f"Success: {result.success}")
    print(f"Output: {result.data}")
    print(f"Executed: {result.executed_stages}")
    print(f"Skipped: {result.skipped_stages}")
    print(f"Errors: {result.errors}")
    print(f"Context: {result.context}")
