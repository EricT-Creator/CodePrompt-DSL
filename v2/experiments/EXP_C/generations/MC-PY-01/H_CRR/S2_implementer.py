"""
MC-PY-01: Plugin-based Data Pipeline
[L]PY310 [D]STDLIB_ONLY [!D]NO_IMPORTLIB [PLUGIN]EXEC [!D]NO_ABC [IFACE]PROTOCOL [TYPE]FULL_HINTS [ERR]ISOLATE [O]CLASS [FILE]SINGLE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


# ─── Protocol Interface ──────────────────────────────────────────────────────

@runtime_checkable
class TransformPlugin(Protocol):
    """Protocol for transform plugins — no ABC."""
    name: str

    def transform(self, data: Any) -> Any:
        ...


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    data: Any
    executed_plugins: list[str]
    skipped_plugins: list[str]
    errors: list[str]


# ─── Dynamic Plugin (from exec'd namespace) ──────────────────────────────────

class DynamicPlugin:
    """Wraps a plugin namespace loaded via exec()."""

    def __init__(self, namespace: dict[str, Any]) -> None:
        self.name: str = namespace.get("name", "unnamed")
        self._transform_fn: Callable[[Any], Any] = namespace.get("transform", lambda x: x)
        self.condition: str | None = namespace.get("condition", None)

    def transform(self, data: Any) -> Any:
        return self._transform_fn(data)

    def __repr__(self) -> str:
        return f"DynamicPlugin(name={self.name!r}, condition={self.condition!r})"


# ─── Plugin Loader (exec, no importlib) ──────────────────────────────────────

def load_plugin(file_path: str) -> DynamicPlugin:
    """Load a single plugin file using exec()."""
    plugin_namespace: dict[str, Any] = {}

    with open(file_path, "r", encoding="utf-8") as f:
        source: str = f.read()

    exec(source, plugin_namespace)

    return DynamicPlugin(plugin_namespace)


def load_plugins_from_directory(directory: str) -> list[DynamicPlugin]:
    """Load all .py files from a directory as plugins."""
    plugins: list[DynamicPlugin] = []
    dir_path: Path = Path(directory)

    if not dir_path.is_dir():
        return plugins

    for file_path in sorted(dir_path.glob("*.py")):
        try:
            plugin: DynamicPlugin = load_plugin(str(file_path))
            plugins.append(plugin)
        except Exception as e:
            print(f"[WARN] Failed to load plugin {file_path.name}: {e}")

    return plugins


# ─── Validate plugin ─────────────────────────────────────────────────────────

def validate_plugin(plugin: Any) -> bool:
    """Check if an object conforms to TransformPlugin protocol."""
    return (
        hasattr(plugin, "name")
        and hasattr(plugin, "transform")
        and callable(getattr(plugin, "transform", None))
    )


# ─── Pipeline Class ──────────────────────────────────────────────────────────

@dataclass
class Pipeline:
    """Orchestrates plugin execution with conditional branching and error isolation."""

    _plugins: list[tuple[Any, str | None]] = field(default_factory=list)
    _conditions: dict[str, Callable[[Any], bool]] = field(default_factory=dict)

    def register(self, plugin: Any, condition_key: str | None = None) -> None:
        """Register a plugin with an optional condition key."""
        if not validate_plugin(plugin):
            raise TypeError(f"Object {plugin!r} does not conform to TransformPlugin protocol")
        self._plugins.append((plugin, condition_key))

    def register_condition(self, key: str, fn: Callable[[Any], bool]) -> None:
        """Register a named condition function."""
        self._conditions[key] = fn

    def load_directory(self, directory: str) -> int:
        """Load and register all plugins from a directory. Returns count loaded."""
        loaded: int = 0
        for plugin in load_plugins_from_directory(directory):
            self._plugins.append((plugin, plugin.condition))
            loaded += 1
        return loaded

    def execute(self, data: Any) -> PipelineResult:
        """Execute all registered plugins in order with error isolation."""
        executed: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []
        current_data: Any = data

        for plugin, condition_key in self._plugins:
            plugin_name: str = getattr(plugin, "name", "unknown")

            # Evaluate condition
            if condition_key is not None:
                condition_fn: Callable[[Any], bool] | None = self._conditions.get(condition_key)
                if condition_fn is not None:
                    try:
                        if not condition_fn(current_data):
                            skipped.append(plugin_name)
                            continue
                    except Exception as e:
                        errors.append(f"{plugin_name}: condition error: {e}")
                        skipped.append(plugin_name)
                        continue
                else:
                    # Unknown condition key → skip
                    skipped.append(plugin_name)
                    continue

            # Execute with error isolation
            try:
                current_data = plugin.transform(current_data)
                executed.append(plugin_name)
            except Exception as e:
                errors.append(f"{plugin_name}: {e}")
                # Continue with unchanged data (error isolation)

        return PipelineResult(
            success=len(errors) == 0,
            data=current_data,
            executed_plugins=executed,
            skipped_plugins=skipped,
            errors=errors,
        )


# ─── Built-in Plugins ────────────────────────────────────────────────────────

class UpperCasePlugin:
    name: str = "UpperCase"

    def transform(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.upper()
        return data


class StripWhitespacePlugin:
    name: str = "StripWhitespace"

    def transform(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.strip()
        return data


class SortListPlugin:
    name: str = "SortList"

    def transform(self, data: Any) -> Any:
        if isinstance(data, list):
            return sorted(data)
        return data


class DoubleNumberPlugin:
    name: str = "DoubleNumber"

    def transform(self, data: Any) -> Any:
        if isinstance(data, (int, float)):
            return data * 2
        return data


# ─── Demo ─────────────────────────────────────────────────────────────────────

def main() -> None:
    pipeline = Pipeline()

    # Register conditions
    pipeline.register_condition("is_string", lambda d: isinstance(d, str))
    pipeline.register_condition("is_list", lambda d: isinstance(d, list))
    pipeline.register_condition("is_number", lambda d: isinstance(d, (int, float)))

    # Register plugins with conditions
    pipeline.register(StripWhitespacePlugin(), condition_key="is_string")
    pipeline.register(UpperCasePlugin(), condition_key="is_string")
    pipeline.register(SortListPlugin(), condition_key="is_list")
    pipeline.register(DoubleNumberPlugin(), condition_key="is_number")

    # Execute with string data
    result1: PipelineResult = pipeline.execute("  hello world  ")
    print(f"String pipeline: {result1}")

    # Execute with list data
    result2: PipelineResult = pipeline.execute([3, 1, 4, 1, 5])
    print(f"List pipeline: {result2}")

    # Execute with number data
    result3: PipelineResult = pipeline.execute(21)
    print(f"Number pipeline: {result3}")


if __name__ == "__main__":
    main()
