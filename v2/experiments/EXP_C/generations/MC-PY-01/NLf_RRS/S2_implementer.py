"""Plugin-Based ETL Data Pipeline — exec-loaded plugins with typing.Protocol."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


# ── Protocol Interface ───────────────────────────────────────────────────────


@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, data: dict[str, Any]) -> dict[str, Any]: ...


# ── Result Dataclasses ───────────────────────────────────────────────────────


@dataclass
class PluginError:
    plugin_name: str
    error_type: str
    message: str
    traceback: str


@dataclass
class PipelineResult:
    success: bool
    data: dict[str, Any]
    errors: list[PluginError] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


# ── Pipeline Configuration ───────────────────────────────────────────────────


@dataclass
class PipelineConfig:
    plugin_paths: list[str] = field(default_factory=list)
    plugin_directory: str | None = None
    on_error: str = "continue"  # "continue" or "abort"
    load_all_classes: bool = False


# ── Plugin Registry ──────────────────────────────────────────────────────────


@dataclass
class PluginEntry:
    plugin: TransformPlugin
    condition: Callable[[dict[str, Any]], bool] | None = None


# ── Pipeline ─────────────────────────────────────────────────────────────────


class Pipeline:
    """Plugin-based ETL data pipeline with exec()-loaded plugins."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self._config: PipelineConfig = config or PipelineConfig()
        self._registry: list[PluginEntry] = []
        self._load_errors: list[PluginError] = []

        # Auto-load from config
        if self._config.plugin_directory:
            self.load_plugins(self._config.plugin_directory)
        for path in self._config.plugin_paths:
            self.load_plugin(path)

    def load_plugin(self, file_path: str) -> None:
        """Read a plugin file and load it via exec()."""
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except (OSError, IOError) as e:
            self._load_errors.append(PluginError(
                plugin_name=file_path,
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc(),
            ))
            return

        namespace: dict[str, Any] = {}
        try:
            exec(source, namespace)
        except Exception as e:
            self._load_errors.append(PluginError(
                plugin_name=file_path,
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc(),
            ))
            return

        # Discover plugin classes
        found = False
        for value in namespace.values():
            if self._is_plugin_class(value):
                try:
                    instance = value()
                    self._registry.append(PluginEntry(plugin=instance))
                    found = True
                    if not self._config.load_all_classes:
                        break
                except Exception as e:
                    self._load_errors.append(PluginError(
                        plugin_name=file_path,
                        error_type=type(e).__name__,
                        message=f"Failed to instantiate: {e}",
                        traceback=traceback.format_exc(),
                    ))

        if not found and not self._load_errors:
            self._load_errors.append(PluginError(
                plugin_name=file_path,
                error_type="DiscoveryError",
                message="No TransformPlugin-compatible class found in file",
                traceback="",
            ))

    def load_plugins(self, directory: str) -> None:
        """Load all .py files from a directory in alphabetical order."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            self._load_errors.append(PluginError(
                plugin_name=directory,
                error_type="NotADirectoryError",
                message=f"{directory} is not a directory",
                traceback="",
            ))
            return

        files = sorted(dir_path.glob("*.py"))
        for f in files:
            self.load_plugin(str(f))

    def register(
        self,
        plugin: TransformPlugin,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Manually register a plugin with an optional condition."""
        self._registry.append(PluginEntry(plugin=plugin, condition=condition))

    def execute(self, data: dict[str, Any]) -> PipelineResult:
        """Run the pipeline on input data, returns the result."""
        current_data = dict(data)
        errors: list[PluginError] = list(self._load_errors)
        skipped: list[str] = []
        overall_success = True

        for entry in self._registry:
            plugin = entry.plugin
            plugin_name = getattr(plugin, "name", plugin.__class__.__name__)

            # Evaluate condition
            if entry.condition is not None:
                try:
                    should_run = entry.condition(current_data)
                except Exception as e:
                    errors.append(PluginError(
                        plugin_name=plugin_name,
                        error_type=type(e).__name__,
                        message=f"Condition evaluation failed: {e}",
                        traceback=traceback.format_exc(),
                    ))
                    skipped.append(plugin_name)
                    continue

                if not should_run:
                    skipped.append(plugin_name)
                    continue

            # Execute plugin
            try:
                result = plugin.transform(current_data)
                current_data = result
            except Exception as e:
                errors.append(PluginError(
                    plugin_name=plugin_name,
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback=traceback.format_exc(),
                ))
                overall_success = False

                if self._config.on_error == "abort":
                    return PipelineResult(
                        success=False,
                        data=current_data,
                        errors=errors,
                        skipped=skipped,
                    )
                # "continue" mode: keep going with unmodified data

        return PipelineResult(
            success=overall_success and len([e for e in errors if e not in self._load_errors]) == 0,
            data=current_data,
            errors=errors,
            skipped=skipped,
        )

    @property
    def plugins(self) -> list[str]:
        """Return names of registered plugins."""
        return [
            getattr(entry.plugin, "name", entry.plugin.__class__.__name__)
            for entry in self._registry
        ]

    @property
    def load_errors(self) -> list[PluginError]:
        """Return errors encountered during plugin loading."""
        return list(self._load_errors)

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _is_plugin_class(obj: Any) -> bool:
        """Check if an object is a class that satisfies the TransformPlugin protocol."""
        if not isinstance(obj, type):
            return False
        if not hasattr(obj, "transform"):
            return False
        if not callable(getattr(obj, "transform", None)):
            return False
        # Check for 'name' attribute (class-level or instance)
        if not hasattr(obj, "name") and "name" not in getattr(obj, "__annotations__", {}):
            return False
        return True


# ── Built-in Example Plugins (for demonstration) ────────────────────────────


class UpperCaseKeysPlugin:
    name: str = "uppercase_keys"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        return {k.upper(): v for k, v in data.items()}


class FilterNullsPlugin:
    name: str = "filter_nulls"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in data.items() if v is not None}


class AddTimestampPlugin:
    name: str = "add_timestamp"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        import time
        result = dict(data)
        result["_processed_at"] = time.time()
        return result


# ── Main (demo) ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = Pipeline()

    # Register plugins manually
    pipeline.register(FilterNullsPlugin())
    pipeline.register(UpperCaseKeysPlugin())
    pipeline.register(
        AddTimestampPlugin(),
        condition=lambda d: d.get("ADD_TIMESTAMP", False),
    )

    # Run pipeline
    input_data = {
        "name": "Alice",
        "email": "alice@example.com",
        "phone": None,
        "add_timestamp": True,
    }

    result = pipeline.execute(input_data)
    print(f"Success: {result.success}")
    print(f"Data: {result.data}")
    print(f"Errors: {result.errors}")
    print(f"Skipped: {result.skipped}")
