"""MC-PY-01: Plugin-based Data Pipeline — exec() loading, Protocol interface, error isolation"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


# ── Protocol interface (no ABC) ─────────────────────────────────────

@runtime_checkable
class TransformProtocol(Protocol):
    def transform(self, data: Any, context: dict[str, Any]) -> Any: ...


# ── Error reporting ─────────────────────────────────────────────────

@dataclass
class PluginError:
    plugin_name: str
    error_type: str
    message: str
    traceback_str: str


@dataclass
class PipelineResult:
    data: Any
    success: bool
    errors: list[PluginError] = field(default_factory=list)
    plugins_executed: list[str] = field(default_factory=list)
    plugins_skipped: list[str] = field(default_factory=list)


# ── Plugin wrapper ──────────────────────────────────────────────────

@dataclass
class Plugin:
    name: str
    transform_func: Callable[[Any, dict[str, Any]], Any]
    condition: str | None = None

    def should_execute(self, context: dict[str, Any]) -> bool:
        if self.condition is None:
            return True
        try:
            safe_globals: dict[str, Any] = {"__builtins__": {}}
            safe_locals: dict[str, Any] = {"context": context}
            return bool(eval(self.condition, safe_globals, safe_locals))
        except Exception:
            return False


# ── DataPipeline class ──────────────────────────────────────────────

class DataPipeline:
    """Plugin-based ETL data pipeline with exec() loading and error isolation."""

    def __init__(self) -> None:
        self._plugins: list[Plugin] = []
        self._errors: list[PluginError] = []

    # ── Plugin loading ──────────────────────────────────────────────

    def add_plugin_from_source(
        self,
        name: str,
        source_code: str,
        condition: str | None = None,
    ) -> bool:
        """Load a plugin from source code string using exec(). Returns True on success."""
        safe_globals: dict[str, Any] = {
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "isinstance": isinstance,
                "type": type,
                "print": print,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "None": None,
                "True": True,
                "False": False,
            }
        }
        try:
            exec(source_code, safe_globals)
        except SyntaxError as e:
            self._errors.append(PluginError(
                plugin_name=name,
                error_type="SyntaxError",
                message=str(e),
                traceback_str=traceback.format_exc(),
            ))
            return False
        except Exception as e:
            self._errors.append(PluginError(
                plugin_name=name,
                error_type=type(e).__name__,
                message=str(e),
                traceback_str=traceback.format_exc(),
            ))
            return False

        transform_fn = safe_globals.get("transform")
        if transform_fn is None or not callable(transform_fn):
            self._errors.append(PluginError(
                plugin_name=name,
                error_type="InterfaceError",
                message="Plugin does not define a callable 'transform' function",
                traceback_str="",
            ))
            return False

        plugin = Plugin(name=name, transform_func=transform_fn, condition=condition)
        self._plugins.append(plugin)
        return True

    def add_plugin_from_file(
        self,
        file_path: str | Path,
        condition: str | None = None,
    ) -> bool:
        """Load a plugin from a .py file using exec()."""
        p = Path(file_path)
        if not p.exists() or not p.suffix == ".py":
            self._errors.append(PluginError(
                plugin_name=str(p.stem),
                error_type="FileError",
                message=f"Plugin file not found or not .py: {p}",
                traceback_str="",
            ))
            return False
        source = p.read_text(encoding="utf-8")
        return self.add_plugin_from_source(name=p.stem, source_code=source, condition=condition)

    def add_plugin_from_callable(
        self,
        name: str,
        func: Callable[[Any, dict[str, Any]], Any],
        condition: str | None = None,
    ) -> None:
        """Register a plugin from an existing callable."""
        self._plugins.append(Plugin(name=name, transform_func=func, condition=condition))

    # ── Execution ───────────────────────────────────────────────────

    def run(self, data: Any, context: dict[str, Any] | None = None) -> PipelineResult:
        """Execute the pipeline: data flows through all plugins sequentially."""
        if context is None:
            context = {}
        result = PipelineResult(data=data, success=True)

        for plugin in self._plugins:
            if not plugin.should_execute(context):
                result.plugins_skipped.append(plugin.name)
                continue

            try:
                data = plugin.transform_func(data, context)
                result.plugins_executed.append(plugin.name)
            except Exception as e:
                err = PluginError(
                    plugin_name=plugin.name,
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback_str=traceback.format_exc(),
                )
                result.errors.append(err)
                # Error isolation: continue to next plugin, data unchanged

        result.data = data
        if result.errors:
            result.success = False
        return result

    # ── Inspection ──────────────────────────────────────────────────

    @property
    def plugins(self) -> list[str]:
        return [p.name for p in self._plugins]

    @property
    def loading_errors(self) -> list[PluginError]:
        return list(self._errors)

    def clear(self) -> None:
        self._plugins.clear()
        self._errors.clear()


# ── Demo / self-test ────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = DataPipeline()

    # Plugin 1: uppercase names
    pipeline.add_plugin_from_source(
        "uppercase",
        """
def transform(data, context):
    if isinstance(data, list):
        return [
            {**item, "name": item["name"].upper()} if isinstance(item, dict) and "name" in item else item
            for item in data
        ]
    return data
""",
    )

    # Plugin 2: filter by premium (conditional)
    pipeline.add_plugin_from_source(
        "premium_filter",
        """
def transform(data, context):
    if isinstance(data, list):
        return [item for item in data if item.get("tier") == "premium"]
    return data
""",
        condition="context.get('user_type') == 'premium'",
    )

    # Plugin 3: intentional error for isolation test
    pipeline.add_plugin_from_source(
        "bad_plugin",
        """
def transform(data, context):
    raise ValueError("intentional error for testing")
""",
    )

    # Plugin 4: add count
    pipeline.add_plugin_from_callable(
        "add_count",
        lambda data, ctx: {"items": data, "count": len(data) if isinstance(data, list) else 0},
    )

    sample = [
        {"name": "alice", "tier": "premium"},
        {"name": "bob", "tier": "free"},
        {"name": "carol", "tier": "premium"},
    ]

    result = pipeline.run(sample, context={"user_type": "premium"})
    print("Success:", result.success)
    print("Executed:", result.plugins_executed)
    print("Skipped:", result.plugins_skipped)
    print("Errors:", [(e.plugin_name, e.message) for e in result.errors])
    print("Output:", result.data)
