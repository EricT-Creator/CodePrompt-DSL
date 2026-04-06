import json
import time
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Union


# ==================== Protocol Definitions ====================

class TransformPlugin(Protocol):
    """Protocol for all transformation plugins."""
    
    def transform(self, data: Any) -> Any:
        """Transform the input data and return the result."""
        ...


class ValidatablePlugin(Protocol):
    """Optional protocol for plugins that can validate their input."""
    
    def validate(self, data: Any) -> bool:
        """Validate if the plugin can handle the given data."""
        ...


class NamedPlugin(Protocol):
    """Optional protocol for plugins that have a name."""
    
    def name(self) -> str:
        """Return the plugin's name."""
        ...


# ==================== Data Classes ====================

@dataclass
class StepReport:
    name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None


@dataclass
class StepError:
    step_name: str
    exception_type: str
    message: str


@dataclass
class PipelineResult:
    output: Any
    steps_executed: List[StepReport]
    steps_skipped: List[str]
    errors: List[StepError]
    
    @property
    def all_successful(self) -> bool:
        return all(step.success for step in self.steps_executed)


@dataclass
class PipelineStep:
    plugin: TransformPlugin
    name: str
    condition: Optional[Callable[[Any], bool]] = None
    
    def should_execute(self, data: Any) -> bool:
        if self.condition is None:
            return True
        return self.condition(data)


# ==================== Plugin Loader ====================

class PluginLoader:
    """Loads plugins from source code strings using exec()."""
    
    @staticmethod
    def load_plugin(source_code: str, plugin_class_name: str = "Plugin") -> TransformPlugin:
        """
        Load a plugin from source code.
        
        Args:
            source_code: The source code string containing the plugin class
            plugin_class_name: The name of the class to instantiate (default: "Plugin")
            
        Returns:
            An instance of the plugin
            
        Raises:
            ValueError: If the plugin cannot be loaded
        """
        namespace: Dict[str, Any] = {}
        
        try:
            exec(source_code, namespace)
        except Exception as e:
            raise ValueError(f"Failed to execute plugin code: {str(e)}")
        
        plugin_class = namespace.get(plugin_class_name)
        if plugin_class is None:
            raise ValueError(f"Plugin class '{plugin_class_name}' not found in source code")
        
        try:
            plugin_instance = plugin_class()
        except Exception as e:
            raise ValueError(f"Failed to instantiate plugin: {str(e)}")
        
        # Verify the instance has the required transform method
        if not hasattr(plugin_instance, 'transform') or not callable(plugin_instance.transform):
            raise ValueError("Plugin does not have a 'transform' method")
        
        return plugin_instance


# ==================== Pipeline Implementation ====================

class Pipeline:
    """Main orchestrator for the plugin-based ETL pipeline."""
    
    def __init__(self, halt_on_error: bool = False):
        self.steps: List[PipelineStep] = []
        self.halt_on_error = halt_on_error
        self._plugin_cache: Dict[str, TransformPlugin] = {}
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """Add a step to the pipeline."""
        self.steps.append(step)
        return self
    
    def create_step(
        self,
        plugin_source: str,
        name: str,
        condition: Optional[Callable[[Any], bool]] = None
    ) -> 'Pipeline':
        """Create and add a step from plugin source code."""
        if name in self._plugin_cache:
            plugin = self._plugin_cache[name]
        else:
            plugin = PluginLoader.load_plugin(plugin_source)
            self._plugin_cache[name] = plugin
        
        step = PipelineStep(
            plugin=plugin,
            name=name,
            condition=condition
        )
        
        return self.add_step(step)
    
    def run(self, data: Any) -> PipelineResult:
        """Execute all steps in the pipeline."""
        current_data = data
        steps_executed: List[StepReport] = []
        steps_skipped: List[str] = []
        errors: List[StepError] = []
        
        for step in self.steps:
            start_time = time.time()
            
            # Check condition
            if not step.should_execute(current_data):
                steps_skipped.append(step.name)
                continue
            
            # Execute step
            try:
                start_transform = time.time()
                
                # Validate if plugin supports validation
                if hasattr(step.plugin, 'validate') and callable(step.plugin.validate):
                    if not step.plugin.validate(current_data):
                        raise ValueError(f"Plugin '{step.name}' rejected the data")
                
                # Transform
                current_data = step.plugin.transform(current_data)
                
                transform_duration = (time.time() - start_transform) * 1000
                steps_executed.append(StepReport(
                    name=step.name,
                    success=True,
                    duration_ms=transform_duration,
                    error=None
                ))
            
            except Exception as e:
                error_duration = (time.time() - start_time) * 1000
                steps_executed.append(StepReport(
                    name=step.name,
                    success=False,
                    duration_ms=error_duration,
                    error=str(e)
                ))
                
                errors.append(StepError(
                    step_name=step.name,
                    exception_type=type(e).__name__,
                    message=str(e)
                ))
                
                if self.halt_on_error:
                    break
        
        return PipelineResult(
            output=current_data,
            steps_executed=steps_executed,
            steps_skipped=steps_skipped,
            errors=errors
        )


    def clear(self) -> None:
        """Clear all steps and cache."""
        self.steps.clear()
        self._plugin_cache.clear()


# ==================== Example Plugins (for demonstration) ====================

# These would typically be loaded from external files

EXAMPLE_PLUGINS = {
    "json_parser": """
import json

class Plugin:
    def transform(self, data):
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {str(e)}")
        return data
    
    def validate(self, data):
        return isinstance(data, str) and data.strip().startswith('{')
    
    def name(self):
        return "json_parser"
""",

    "csv_parser": """
import csv
from io import StringIO

class Plugin:
    def transform(self, data):
        if isinstance(data, str):
            reader = csv.DictReader(StringIO(data))
            return [row for row in reader]
        return data
    
    def validate(self, data):
        return isinstance(data, str) and ',' in data
    
    def name(self):
        return "csv_parser"
""",

    "text_filter": """
import re

class Plugin:
    def __init__(self):
        self.pattern = r'[A-Za-z]+'
    
    def transform(self, data):
        if isinstance(data, str):
            matches = re.findall(self.pattern, data)
            return ' '.join(matches)
        return data
    
    def validate(self, data):
        return isinstance(data, str) and len(data) > 0
    
    def name(self):
        return "text_filter"
""",

    "number_multiplier": """
class Plugin:
    def __init__(self, factor=2):
        self.factor = factor
    
    def transform(self, data):
        if isinstance(data, (int, float)):
            return data * self.factor
        return data
    
    def validate(self, data):
        return isinstance(data, (int, float))
    
    def name(self):
        return "number_multiplier"
""",

    "list_reverser": """
class Plugin:
    def transform(self, data):
        if isinstance(data, list):
            return list(reversed(data))
        return data
    
    def validate(self, data):
        return isinstance(data, list)
    
    def name(self):
        return "list_reverser"
"""
}


# ==================== Usage Example ====================

def example_usage():
    """Example of how to use the pipeline with plugins."""
    
    # Create pipeline
    pipeline = Pipeline(halt_on_error=False)
    
    # Add plugins from source code
    pipeline.create_step(
        plugin_source=EXAMPLE_PLUGINS["json_parser"],
        name="json_parser"
    )
    
    pipeline.create_step(
        plugin_source=EXAMPLE_PLUGINS["number_multiplier"],
        name="number_multiplier"
    )
    
    pipeline.create_step(
        plugin_source=EXAMPLE_PLUGINS["list_reverser"],
        name="list_reverser",
        condition=lambda data: isinstance(data, list) and len(data) > 5
    )
    
    # Example data
    test_data = '{"numbers": [1, 2, 3, 4, 5, 6, 7]}'
    
    # Run pipeline
    result = pipeline.run(test_data)
    
    # Display results
    print("Pipeline Execution Report:")
    print(f"  Input: {test_data}")
    print(f"  Output: {result.output}")
    print(f"  Steps Executed: {len(result.steps_executed)}")
    print(f"  Steps Skipped: {len(result.steps_skipped)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  All Successful: {result.all_successful}")
    
    if result.steps_skipped:
        print(f"  Skipped Steps: {', '.join(result.steps_skipped)}")
    
    if result.errors:
        print("  Error Details:")
        for error in result.errors:
            print(f"    - {error.step_name}: {error.exception_type}: {error.message}")
    
    return result


# ==================== Main Execution ====================

if __name__ == "__main__":
    # Run example usage
    result = example_usage()
    
    print("\n" + "="*60)
    print("Pipeline completed successfully!")
    print("="*60)