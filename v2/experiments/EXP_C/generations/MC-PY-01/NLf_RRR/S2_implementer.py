"""Plugin-Based ETL Data Pipeline — Python 3.10+ standard library only."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


# ─── Protocol ─────────────────────────────────────────────────


@runtime_checkable
class TransformPlugin(Protocol):
    name: str

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        ...


# ─── Dataclasses ──────────────────────────────────────────────


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
    errors: list[PluginError]
    skipped: list[str]


@dataclass
class PipelineConfig:
    plugin_paths: list[str] = field(default_factory=list)
    plugin_directory: str | None = None
    fail_mode: str = "continue"  # "continue" or "abort"


# ─── Plugin Registry ─────────────────────────────────────────


@dataclass
class RegisteredPlugin:
    plugin: TransformPlugin
    condition: Callable[[dict[str, Any]], bool] | None


# ─── Pipeline Class ───────────────────────────────────────────


class Pipeline:
    """Plugin-based ETL data pipeline.

    Loads plugins at runtime via exec(), runs them in sequence,
    supports conditional branches, and isolates errors.
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self._config: PipelineConfig = config or PipelineConfig()
        self._registry: list[RegisteredPlugin] = []
        self._load_errors: list[PluginError] = []

    def load_plugin(self, file_path: str) -> None:
        """Read a plugin file and load it via exec()."""
        path = Path(file_path)
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as exc:
            self._load_errors.append(
                PluginError(
                    plugin_name=path.name,
                    error_type=type(exc).__name__,
                    message=str(exc),
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
                    message=str(exc),
                    traceback=traceback.format_exc(),
                )
            )
            return

        # Discover plugin classes
        found = False
        for value in namespace.values():
            if (
                isinstance(value, type)
                and value is not object
                and hasattr(value, "transform")
                and hasattr(value, "name")
            ):
                try:
                    instance = value()
                    if isinstance(instance, TransformPlugin):
                        self.register(instance)
                        found = True
                        break  # Only first qualifying class per file
                except Exception as exc:
                    self._load_errors.append(
                        PluginError(
                            plugin_name=path.name,
                            error_type=type(exc).__name__,
                            message=f"Failed to instantiate {value}: {exc}",
                            traceback=traceback.format_exc(),
                        )
                    )

        if not found and not self._load_errors:
            self._load_errors.append(
                PluginError(
                    plugin_name=path.name,
                    error_type="PluginNotFound",
                    message=f"No TransformPlugin class found in {path.name}",
                    traceback="",
                )
            )

    def load_plugins(self, directory: str) -> None:
        """Load all .py files from a directory in alphabetical order."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            self._load_errors.append(
                PluginError(
                    plugin_name=directory,
                    error_type="NotADirectoryError",
                    message=f"{directory} is not a directory",
                    traceback="",
                )
            )
            return

        plugin_files = sorted(dir_path.glob("*.py"))
        for pf in plugin_files:
            self.load_plugin(str(pf))

    def register(
        self,
        plugin: TransformPlugin,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Manually register a plugin with an optional condition."""
        self._registry.append(RegisteredPlugin(plugin=plugin, condition=condition))

    def execute(self, data: dict[str, Any]) -> PipelineResult:
        """Run the pipeline on input data, returns the result."""
        current_data = dict(data)  # shallow copy
        errors: list[PluginError] = list(self._load_errors)
        skipped: list[str] = []
        success = True

        for entry in self._registry:
            plugin = entry.plugin
            condition = entry.condition
            plugin_name = getattr(plugin, "name", plugin.__class__.__name__)

            # Evaluate condition
            if condition is not None:
                try:
                    should_run = condition(current_data)
                except Exception as exc:
                    errors.append(
                        PluginError(
                            plugin_name=plugin_name,
                            error_type=type(exc).__name__,
                            message=f"Condition evaluation failed: {exc}",
                            traceback=traceback.format_exc(),
                        )
                    )
                    skipped.append(plugin_name)
                    continue

                if not should_run:
                    skipped.append(plugin_name)
                    continue

            # Execute plugin
            try:
                result_data = plugin.transform(current_data)
                current_data = result_data
            except Exception as exc:
                errors.append(
                    PluginError(
                        plugin_name=plugin_name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        traceback=traceback.format_exc(),
                    )
                )
                success = False

                if self._config.fail_mode == "abort":
                    return PipelineResult(
                        success=False,
                        data=current_data,
                        errors=errors,
                        skipped=skipped,
                    )
                # In "continue" mode, proceed with unmodified data

        if errors:
            success = False

        return PipelineResult(
            success=success,
            data=current_data,
            errors=errors,
            skipped=skipped,
        )


# ─── Built-in Example Plugins (for demonstration) ────────────


class UpperCasePlugin:
    name: str = "uppercase"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = v.upper()
            else:
                result[k] = v
        return result


class FilterNullPlugin:
    name: str = "filter_null"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in data.items() if v is not None}


class AddTimestampPlugin:
    name: str = "add_timestamp"

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        data["_processed_at"] = datetime.now(timezone.utc).isoformat()
        return data


# ─── Main (demonstration) ────────────────────────────────────

if __name__ == "__main__":
    pipeline = Pipeline(PipelineConfig(fail_mode="continue"))

    # Register built-in plugins
    pipeline.register(FilterNullPlugin())
    pipeline.register(
        UpperCasePlugin(),
        condition=lambda d: d.get("format") == "text",
    )
    pipeline.register(AddTimestampPlugin())

    # Execute
    input_data = {
        "name": "Alice",
        "email": "alice@example.com",
        "phone": None,
        "format": "text",
    }

    result = pipeline.execute(input_data)
    print(f"Success: {result.success}")
    print(f"Data: {result.data}")
    print(f"Errors: {result.errors}")
    print(f"Skipped: {result.skipped}")
