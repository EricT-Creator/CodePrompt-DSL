"""Plugin-Based ETL Data Pipeline."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


# ── Protocol ─────────────────────────────────────────────────────────────────


@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        ...


# ── Data Classes ─────────────────────────────────────────────────────────────


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


@dataclass
class PipelineConfig:
    plugin_paths: list[str] = field(default_factory=list)
    plugin_directory: str | None = None
    fail_mode: str = "continue"  # "continue" or "abort"
    load_all_classes: bool = False


# ── Pipeline ─────────────────────────────────────────────────────────────────


class Pipeline:
    """Plugin-based ETL data pipeline with conditional branches and error isolation."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self._config: PipelineConfig = config or PipelineConfig()
        self._registry: list[
            tuple[TransformPlugin, Callable[[dict[str, Any]], bool] | None]
        ] = []
        self._load_errors: list[PluginError] = []

    # ── Plugin Loading ───────────────────────────────────────────────────

    def load_plugin(self, file_path: str) -> None:
        """Read a plugin file and load it via exec()."""
        path = Path(file_path)
        try:
            source: str = path.read_text(encoding="utf-8")
        except Exception as exc:
            self._load_errors.append(
                PluginError(
                    plugin_name=path.name,
                    error_type=type(exc).__name__,
                    message=f"Failed to read plugin file: {exc}",
                    traceback=traceback.format_exc(),
                )
            )
            return

        namespace: dict[str, Any] = {}
        try:
            exec(source, namespace)
        except Exception as exc:
            self._load_errors.append(
                PluginError(
                    plugin_name=path.name,
                    error_type=type(exc).__name__,
                    message=f"Failed to execute plugin file: {exc}",
                    traceback=traceback.format_exc(),
                )
            )
            return

        found = False
        for value in namespace.values():
            if self._is_plugin_class(value):
                try:
                    instance = value()
                    self.register(instance)
                    found = True
                    if not self._config.load_all_classes:
                        break
                except Exception as exc:
                    self._load_errors.append(
                        PluginError(
                            plugin_name=getattr(value, "__name__", path.name),
                            error_type=type(exc).__name__,
                            message=f"Failed to instantiate plugin: {exc}",
                            traceback=traceback.format_exc(),
                        )
                    )

        if not found and not self._load_errors:
            self._load_errors.append(
                PluginError(
                    plugin_name=path.name,
                    error_type="PluginNotFound",
                    message="No valid TransformPlugin class found in file",
                    traceback="",
                )
            )

    def load_plugins(self, directory: str) -> None:
        """Load all .py plugin files from a directory in alphabetical order."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            self._load_errors.append(
                PluginError(
                    plugin_name=directory,
                    error_type="NotADirectoryError",
                    message=f"Plugin directory does not exist: {directory}",
                    traceback="",
                )
            )
            return

        files = sorted(dir_path.glob("*.py"))
        for f in files:
            self.load_plugin(str(f))

    def register(
        self,
        plugin: TransformPlugin,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Register a plugin with an optional condition."""
        self._registry.append((plugin, condition))

    # ── Execution ────────────────────────────────────────────────────────

    def execute(self, data: dict[str, Any]) -> PipelineResult:
        """Run the pipeline on input data, returns result."""
        current_data: dict[str, Any] = dict(data)
        errors: list[PluginError] = list(self._load_errors)
        skipped: list[str] = []
        success = True

        for plugin, condition in self._registry:
            plugin_name: str = getattr(plugin, "name", type(plugin).__name__)

            # Evaluate condition
            if condition is not None:
                try:
                    should_run = condition(current_data)
                except Exception:
                    should_run = False

                if not should_run:
                    skipped.append(plugin_name)
                    continue

            # Execute plugin with error isolation
            try:
                result = plugin.transform(current_data)
                current_data = result
            except Exception as exc:
                error = PluginError(
                    plugin_name=plugin_name,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    traceback=traceback.format_exc(),
                )
                errors.append(error)
                success = False

                if self._config.fail_mode == "abort":
                    return PipelineResult(
                        success=False,
                        data=current_data,
                        errors=errors,
                        skipped=skipped,
                    )
                # "continue" mode: keep going with unmodified data

        return PipelineResult(
            success=success and len(errors) == 0,
            data=current_data,
            errors=errors,
            skipped=skipped,
        )

    # ── Introspection ────────────────────────────────────────────────────

    @property
    def plugins(self) -> list[str]:
        """Return names of registered plugins."""
        return [
            getattr(p, "name", type(p).__name__) for p, _ in self._registry
        ]

    @property
    def load_errors(self) -> list[PluginError]:
        """Return errors encountered during plugin loading."""
        return list(self._load_errors)

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_plugin_class(obj: Any) -> bool:
        """Check if an object is a class that satisfies the TransformPlugin protocol."""
        if not isinstance(obj, type):
            return False
        if obj is object:
            return False
        has_transform = hasattr(obj, "transform") and callable(
            getattr(obj, "transform", None)
        )
        has_name = hasattr(obj, "name")
        return has_transform and has_name


# ── Built-in Example Plugins ────────────────────────────────────────────────


class UpperCasePlugin:
    name: str = "uppercase"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = value.upper()
            else:
                result[key] = value
        return result


class FilterKeysPlugin:
    name: str = "filter_keys"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        allowed = data.get("_allowed_keys", None)
        if allowed is None:
            return data
        return {k: v for k, v in data.items() if k in allowed or k.startswith("_")}


class AddTimestampPlugin:
    name: str = "add_timestamp"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        result = dict(data)
        result["_processed_at"] = datetime.now(timezone.utc).isoformat()
        return result


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = Pipeline(PipelineConfig(fail_mode="continue"))

    # Register built-in plugins with conditions
    pipeline.register(AddTimestampPlugin())
    pipeline.register(
        UpperCasePlugin(),
        condition=lambda d: d.get("format") != "binary",
    )
    pipeline.register(
        FilterKeysPlugin(),
        condition=lambda d: "_allowed_keys" in d,
    )

    # Execute pipeline
    input_data = {
        "name": "hello world",
        "count": 42,
        "format": "text",
    }

    result = pipeline.execute(input_data)
    print(f"Success: {result.success}")
    print(f"Data: {result.data}")
    print(f"Errors: {result.errors}")
    print(f"Skipped: {result.skipped}")
