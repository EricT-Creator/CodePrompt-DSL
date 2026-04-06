from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


# ── Exceptions ──────────────────────────────────────────────────────────

class PipelineError(Exception):
    pass


class PluginLoadError(PipelineError):
    pass


class PluginExecutionError(PipelineError):
    pass


class PipelineCriticalError(PipelineError):
    pass


# ── Protocol interface ──────────────────────────────────────────────────

@runtime_checkable
class TransformPlugin(Protocol):
    def transform(self, context: dict[str, Any]) -> Any:
        ...


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class PluginMetadata:
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    path: str = ""


@dataclass
class PluginResult:
    success: bool
    output: Any = None
    error: str = ""
    execution_time: float = 0.0
    plugin_id: str = ""


@dataclass
class PipelineMetrics:
    total_plugins: int = 0
    executed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_plugins": self.total_plugins,
            "executed": self.executed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "execution_time": round(self.execution_time, 4),
        }


@dataclass
class ErrorRecord:
    plugin_id: str
    error_type: str
    message: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {"plugin_id": self.plugin_id, "error_type": self.error_type, "message": self.message, "timestamp": self.timestamp}


@dataclass
class PipelineResult:
    success: bool
    output: Any
    metrics: PipelineMetrics
    errors: list[ErrorRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "error_count": self.error_count,
            "metrics": self.metrics.to_dict(),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


# ── Plugin Wrapper ──────────────────────────────────────────────────────

class PluginWrapper:
    def __init__(self, plugin_path: str, condition: str | None = None) -> None:
        self.plugin_path: str = plugin_path
        self.plugin_id: str = f"plug_{uuid.uuid4().hex[:8]}"
        self.condition: str | None = condition
        self.instance: Any = None
        self.metadata: PluginMetadata = PluginMetadata(path=plugin_path)
        self.is_loaded: bool = False
        self.load_error: str = ""

    def load(self) -> bool:
        try:
            source = Path(self.plugin_path).read_text(encoding="utf-8")
        except Exception as exc:
            self.load_error = f"Cannot read file: {exc}"
            return False

        namespace: dict[str, Any] = {
            "__file__": self.plugin_path,
            "__name__": f"plugin_{self.plugin_id}",
        }

        try:
            exec(source, namespace)
        except Exception as exc:
            self.load_error = f"exec failed: {exc}"
            return False

        plugin_cls = None
        for obj in namespace.values():
            if isinstance(obj, type) and obj.__name__ != "object":
                if hasattr(obj, "transform") and callable(getattr(obj, "transform")):
                    plugin_cls = obj
                    break

        if plugin_cls is None:
            self.load_error = "No class with transform() found"
            return False

        try:
            self.instance = plugin_cls()
        except Exception as exc:
            self.load_error = f"Instantiation failed: {exc}"
            return False

        self.metadata.name = getattr(self.instance, "name", plugin_cls.__name__)
        self.metadata.version = getattr(self.instance, "version", "1.0.0")
        self.metadata.description = getattr(self.instance, "description", "")
        self.is_loaded = True
        return True

    def execute(self, context: dict[str, Any]) -> PluginResult:
        if not self.is_loaded:
            return PluginResult(success=False, error=self.load_error, plugin_id=self.plugin_id)

        start = time.perf_counter()
        try:
            output = self.instance.transform(context)
            elapsed = time.perf_counter() - start
            return PluginResult(success=True, output=output, execution_time=elapsed, plugin_id=self.plugin_id)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            return PluginResult(success=False, error=str(exc), execution_time=elapsed, plugin_id=self.plugin_id)

    def should_execute(self, context: dict[str, Any]) -> bool:
        if self.condition is None:
            return True
        try:
            safe_globals: dict[str, Any] = {"__builtins__": {}, "len": len, "str": str, "int": int, "float": float, "bool": bool, "abs": abs, "min": min, "max": max}
            return bool(eval(compile(self.condition, "<cond>", "eval"), safe_globals, {"ctx": context}))
        except Exception:
            return False


# ── Pipeline ────────────────────────────────────────────────────────────

class Pipeline:
    def __init__(
        self,
        name: str = "default",
        max_errors: int = 0,
        error_isolation: bool = True,
    ) -> None:
        self.name: str = name
        self.max_errors: int = max_errors
        self.error_isolation: bool = error_isolation
        self._plugins: list[PluginWrapper] = []

    # ── Plugin management ───────────────────────────────────────────────

    def add_plugin(self, plugin_path: str, condition: str | None = None) -> str:
        pw = PluginWrapper(plugin_path, condition=condition)
        pw.load()
        self._plugins.append(pw)
        return pw.plugin_id

    def remove_plugin(self, plugin_id: str) -> bool:
        before = len(self._plugins)
        self._plugins = [p for p in self._plugins if p.plugin_id != plugin_id]
        return len(self._plugins) < before

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    # ── Execution ───────────────────────────────────────────────────────

    def run(self, input_data: Any = None) -> PipelineResult:
        context: dict[str, Any] = {"input": input_data, "intermediate": {}, "pipeline_name": self.name}
        metrics = PipelineMetrics(total_plugins=len(self._plugins))
        errors: list[ErrorRecord] = []
        warnings: list[str] = []
        start = time.perf_counter()

        for pw in self._plugins:
            if not pw.is_loaded:
                metrics.skipped += 1
                errors.append(ErrorRecord(plugin_id=pw.plugin_id, error_type="LoadError", message=pw.load_error))
                if self._should_stop(errors):
                    break
                continue

            if not pw.should_execute(context):
                metrics.skipped += 1
                continue

            result = pw.execute(context)
            metrics.executed += 1

            if result.success:
                metrics.succeeded += 1
                context["intermediate"][pw.plugin_id] = result.output
                context["input"] = result.output
            else:
                metrics.failed += 1
                rec = ErrorRecord(plugin_id=pw.plugin_id, error_type="ExecutionError", message=result.error)
                errors.append(rec)
                if not self.error_isolation:
                    break
                if self._should_stop(errors):
                    break

        metrics.execution_time = time.perf_counter() - start
        return PipelineResult(
            success=metrics.failed == 0,
            output=context.get("input"),
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    def _should_stop(self, errors: list[ErrorRecord]) -> bool:
        if self.max_errors > 0 and len(errors) >= self.max_errors:
            return True
        return False


# ── Demo / CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import tempfile
    import textwrap

    plugin_code = textwrap.dedent("""\
    class UpperPlugin:
        name = "upper"
        version = "1.0.0"
        description = "Uppercases input string"

        def transform(self, context):
            data = context.get("input", "")
            return str(data).upper()
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(plugin_code)
        f.flush()
        tmp_path = f.name

    pipe = Pipeline(name="demo", max_errors=5)
    pipe.add_plugin(tmp_path)
    result = pipe.run(input_data="hello world")
    print(result.to_dict())
