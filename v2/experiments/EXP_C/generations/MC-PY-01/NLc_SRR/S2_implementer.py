"""
MC-PY-01: Plugin-based ETL Data Pipeline
Engineering Constraints: Python 3.10+, stdlib only. exec() for plugin loading, no importlib.
Protocol for interfaces, no ABC. Full type annotations. Plugin errors isolated. Single file, class output.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

# ── Errors ──────────────────────────────────────────────────────────────


class PipelineError(Exception):
    def __init__(self, message: str, plugin_name: str = "", recoverable: bool = True) -> None:
        super().__init__(message)
        self.plugin_name = plugin_name
        self.recoverable = recoverable


class PluginLoadError(PipelineError):
    pass


class ConditionError(PipelineError):
    pass


# ── Data classes ────────────────────────────────────────────────────────


@dataclass
class PipelineContext:
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    current_plugin: Optional[str] = None
    branch_conditions: Dict[str, bool] = field(default_factory=dict)

    def add_error(self, plugin_name: str, error_type: str, message: str, recoverable: bool = True) -> None:
        self.errors.append({
            "plugin": plugin_name,
            "type": error_type,
            "message": message,
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat(),
        })

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update_metadata(self, **kwargs: Any) -> None:
        self.metadata.update(kwargs)


@dataclass
class PipelineResult:
    success: bool
    data: Dict[str, Any]
    errors: List[Dict[str, Any]]
    execution_time: float
    plugins_executed: List[str]
    plugins_skipped: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "execution_time": self.execution_time,
            "plugins_executed": self.plugins_executed,
            "plugins_skipped": self.plugins_skipped,
            "error_count": len(self.errors),
            "data_keys": list(self.data.keys()),
        }


# ── Protocol ────────────────────────────────────────────────────────────


@runtime_checkable
class TransformPlugin(Protocol):
    def transform(self, context: PipelineContext) -> PipelineContext: ...
    def get_name(self) -> str: ...
    def get_description(self) -> str: ...
    def get_version(self) -> str: ...


# ── Plugin Loader (exec-based) ──────────────────────────────────────────


class PluginLoader:
    def __init__(self) -> None:
        self.loaded_plugins: Dict[str, TransformPlugin] = {}
        self.plugin_sources: Dict[str, str] = {}

    def load_from_source(self, plugin_name: str, source_code: str) -> TransformPlugin:
        self._validate_source(source_code)

        namespace: Dict[str, Any] = {
            "__name__": f"plugin_{plugin_name}",
            "__builtins__": {
                "len": len, "str": str, "int": int, "float": float, "bool": bool,
                "list": list, "dict": dict, "tuple": tuple, "set": set,
                "range": range, "enumerate": enumerate, "zip": zip,
                "map": map, "filter": filter, "sorted": sorted,
                "min": min, "max": max, "sum": sum, "abs": abs,
                "isinstance": isinstance, "issubclass": issubclass,
                "print": print, "type": type, "hasattr": hasattr,
                "getattr": getattr, "setattr": setattr,
                "ValueError": ValueError, "TypeError": TypeError,
                "KeyError": KeyError, "Exception": Exception,
                "None": None, "True": True, "False": False,
            },
            "PipelineContext": PipelineContext,
            "PipelineError": PipelineError,
        }

        try:
            exec(source_code, namespace)
        except SyntaxError as e:
            raise PluginLoadError(f"Syntax error in plugin '{plugin_name}': {e}", plugin_name)
        except Exception as e:
            raise PluginLoadError(f"Exec error in plugin '{plugin_name}': {e}", plugin_name)

        plugin_class = self._find_plugin_class(namespace)
        if plugin_class is None:
            raise PluginLoadError(f"No plugin class found in '{plugin_name}'", plugin_name)

        try:
            instance = plugin_class()
        except Exception as e:
            raise PluginLoadError(f"Instantiation failed for '{plugin_name}': {e}", plugin_name)

        if not self._validate_plugin(instance):
            raise PluginLoadError(f"Plugin '{plugin_name}' does not satisfy TransformPlugin protocol", plugin_name)

        self.loaded_plugins[plugin_name] = instance
        self.plugin_sources[plugin_name] = source_code
        return instance

    def _validate_source(self, source: str) -> None:
        forbidden = ["import os", "import sys", "import subprocess", "__import__"]
        for f in forbidden:
            if f in source:
                raise PluginLoadError(f"Forbidden pattern in source: {f}")

    def _find_plugin_class(self, namespace: Dict[str, Any]) -> Optional[type]:
        for name, obj in namespace.items():
            if isinstance(obj, type) and name != "PipelineContext" and name != "PipelineError":
                if hasattr(obj, "transform") and hasattr(obj, "get_name") and hasattr(obj, "get_description"):
                    return obj
        return None

    def _validate_plugin(self, instance: Any) -> bool:
        for method in ("transform", "get_name", "get_description", "get_version"):
            if not hasattr(instance, method) or not callable(getattr(instance, method)):
                return False
        return True


# ── Plugin Registry ─────────────────────────────────────────────────────


class PluginRegistry:
    def __init__(self) -> None:
        self.plugins: Dict[str, TransformPlugin] = {}
        self.categories: Dict[str, List[str]] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def register(self, plugin: TransformPlugin, category: str = "default", deps: Optional[List[str]] = None) -> None:
        name = plugin.get_name()
        self.plugins[name] = plugin
        self.categories.setdefault(category, []).append(name)
        self.dependencies[name] = deps or []

    def get(self, name: str) -> Optional[TransformPlugin]:
        return self.plugins.get(name)

    def list_by_category(self, category: str) -> List[str]:
        return self.categories.get(category, [])


# ── Condition Parser ────────────────────────────────────────────────────


class ConditionParser:
    def evaluate(self, condition_str: str, context: PipelineContext) -> bool:
        resolved = self._resolve_vars(condition_str, context)
        safe_builtins = {"len": len, "str": str, "int": int, "float": float, "bool": bool, "True": True, "False": False, "None": None}
        try:
            return bool(eval(resolved, {"__builtins__": safe_builtins}))
        except Exception as e:
            raise ConditionError(f"Condition eval failed: '{condition_str}' -> {e}")

    def _resolve_vars(self, expr: str, ctx: PipelineContext) -> str:
        def replacer(match: re.Match[str]) -> str:
            source = match.group(1)
            key = match.group(2)
            val = ctx.data.get(key) if source == "data" else ctx.metadata.get(key)
            return repr(val)
        return re.sub(r"(data|metadata)\.(\w+)", replacer, expr)


# ── Pipeline ────────────────────────────────────────────────────────────


@dataclass
class BranchDef:
    name: str
    condition: str
    plugins: List[str]
    else_plugins: List[str] = field(default_factory=list)


class DataPipeline:
    def __init__(self, name: str = "pipeline", error_isolation: bool = True) -> None:
        self.name = name
        self.error_isolation = error_isolation
        self.registry = PluginRegistry()
        self.loader = PluginLoader()
        self.condition_parser = ConditionParser()
        self.plugin_order: List[str] = []
        self.branches: List[BranchDef] = []

    def add_plugin(self, plugin: TransformPlugin, category: str = "default") -> None:
        self.registry.register(plugin, category)
        self.plugin_order.append(plugin.get_name())

    def load_plugin_source(self, name: str, source: str, category: str = "default") -> TransformPlugin:
        plugin = self.loader.load_from_source(name, source)
        self.registry.register(plugin, category)
        self.plugin_order.append(name)
        return plugin

    def add_branch(self, name: str, condition: str, plugins: List[str], else_plugins: Optional[List[str]] = None) -> None:
        self.branches.append(BranchDef(name=name, condition=condition, plugins=plugins, else_plugins=else_plugins or []))

    def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> PipelineResult:
        context = PipelineContext(data=initial_data or {})
        executed: List[str] = []
        skipped: List[str] = []
        start = time.time()

        # Execute ordered plugins
        for plugin_name in self.plugin_order:
            plugin = self.registry.get(plugin_name)
            if not plugin:
                skipped.append(plugin_name)
                continue

            context.current_plugin = plugin_name
            try:
                context = plugin.transform(context)
                executed.append(plugin_name)
            except Exception as e:
                context.add_error(plugin_name, type(e).__name__, str(e), recoverable=self.error_isolation)
                if not self.error_isolation:
                    break
                skipped.append(plugin_name)

        # Execute branches
        for branch in self.branches:
            try:
                cond_result = self.condition_parser.evaluate(branch.condition, context)
                context.branch_conditions[branch.name] = cond_result
                targets = branch.plugins if cond_result else branch.else_plugins
                for pname in targets:
                    plugin = self.registry.get(pname)
                    if plugin:
                        context.current_plugin = pname
                        try:
                            context = plugin.transform(context)
                            executed.append(pname)
                        except Exception as e:
                            context.add_error(pname, type(e).__name__, str(e))
                            if not self.error_isolation:
                                break
                            skipped.append(pname)
                    else:
                        skipped.append(pname)
            except ConditionError as e:
                context.add_error(branch.name, "ConditionError", str(e))

        elapsed = time.time() - start
        return PipelineResult(
            success=len(context.errors) == 0,
            data=context.data,
            errors=context.errors,
            execution_time=elapsed,
            plugins_executed=executed,
            plugins_skipped=skipped,
        )


# ── Built-in Plugins ───────────────────────────────────────────────────


class CSVReaderPlugin:
    def __init__(self, csv_text: str = "", delimiter: str = ",") -> None:
        self._csv_text = csv_text
        self._delimiter = delimiter

    def get_name(self) -> str:
        return "csv_reader"

    def get_description(self) -> str:
        return "Reads CSV text and outputs list of dicts"

    def get_version(self) -> str:
        return "1.0.0"

    def transform(self, context: PipelineContext) -> PipelineContext:
        text = self._csv_text or context.get_data("csv_text", "")
        if not text:
            raise PipelineError("No CSV data", "csv_reader")
        reader = csv.DictReader(io.StringIO(text), delimiter=self._delimiter)
        rows = list(reader)
        context.set_data("rows", rows)
        context.update_metadata(row_count=len(rows))
        return context


class FilterPlugin:
    def __init__(self, field_name: str = "", value: Any = None) -> None:
        self._field = field_name
        self._value = value

    def get_name(self) -> str:
        return "filter"

    def get_description(self) -> str:
        return "Filters rows by field value"

    def get_version(self) -> str:
        return "1.0.0"

    def transform(self, context: PipelineContext) -> PipelineContext:
        rows: List[Dict[str, Any]] = context.get_data("rows", [])
        if self._field and self._value is not None:
            rows = [r for r in rows if r.get(self._field) == self._value]
        context.set_data("rows", rows)
        context.update_metadata(filtered_count=len(rows))
        return context


class MapPlugin:
    def __init__(self, func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> None:
        self._func = func or (lambda x: x)

    def get_name(self) -> str:
        return "map_transform"

    def get_description(self) -> str:
        return "Applies a function to each row"

    def get_version(self) -> str:
        return "1.0.0"

    def transform(self, context: PipelineContext) -> PipelineContext:
        rows: List[Dict[str, Any]] = context.get_data("rows", [])
        context.set_data("rows", [self._func(r) for r in rows])
        return context


class JSONOutputPlugin:
    def get_name(self) -> str:
        return "json_output"

    def get_description(self) -> str:
        return "Converts rows to JSON string"

    def get_version(self) -> str:
        return "1.0.0"

    def transform(self, context: PipelineContext) -> PipelineContext:
        rows = context.get_data("rows", [])
        context.set_data("json_output", json.dumps(rows, indent=2, ensure_ascii=False))
        return context


class AggregatePlugin:
    def __init__(self, field_name: str = "", operation: str = "count") -> None:
        self._field = field_name
        self._op = operation

    def get_name(self) -> str:
        return "aggregate"

    def get_description(self) -> str:
        return "Aggregates data"

    def get_version(self) -> str:
        return "1.0.0"

    def transform(self, context: PipelineContext) -> PipelineContext:
        rows: List[Dict[str, Any]] = context.get_data("rows", [])
        if self._op == "count":
            context.set_data("aggregate_result", len(rows))
        elif self._op == "sum" and self._field:
            total = sum(float(r.get(self._field, 0)) for r in rows)
            context.set_data("aggregate_result", total)
        elif self._op == "avg" and self._field:
            vals = [float(r.get(self._field, 0)) for r in rows]
            context.set_data("aggregate_result", sum(vals) / len(vals) if vals else 0)
        return context


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = DataPipeline("demo_pipeline")

    sample_csv = "name,age,city\nAlice,30,NYC\nBob,25,London\nCharlie,35,NYC\nDiana,28,Tokyo"
    pipeline.add_plugin(CSVReaderPlugin(csv_text=sample_csv))
    pipeline.add_plugin(AggregatePlugin(field_name="age", operation="avg"))
    pipeline.add_plugin(JSONOutputPlugin())

    # Load a plugin via exec
    dynamic_source = '''
class UppercaseNamePlugin:
    def get_name(self):
        return "uppercase_names"
    def get_description(self):
        return "Uppercases all name fields"
    def get_version(self):
        return "1.0.0"
    def transform(self, context):
        rows = context.get_data("rows", [])
        for r in rows:
            if "name" in r:
                r["name"] = str(r["name"]).upper()
        context.set_data("rows", rows)
        return context
'''
    pipeline.load_plugin_source("uppercase_names", dynamic_source)

    result = pipeline.execute()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\nRows: {result.data.get('rows')}")
    print(f"Average age: {result.data.get('aggregate_result')}")
