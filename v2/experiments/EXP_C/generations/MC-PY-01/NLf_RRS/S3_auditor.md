## Constraint Review
- C1 (Python 3.10+, stdlib): PASS — from __future__ import annotations, uses only standard library imports
- C2 (exec() loading, no importlib): PASS — load_plugin method uses exec(source, namespace) for plugin loading
- C3 (Protocol, no ABC): PASS — defines TransformPlugin protocol with @runtime_checkable decorator, no ABC used
- C4 (Full type annotations): PASS — all public methods and class attributes have complete type annotations
- C5 (Error isolation): PASS — PluginError dataclass and error handling ensures one plugin failure doesn't crash pipeline
- C6 (Single file, class): PASS — entire implementation in single file with Pipeline class as main output

## Functionality Assessment (0-5)
Score: 5 — Code implements a complete plugin-based ETL pipeline with exec() loading, error isolation, conditional execution, and proper protocol interfaces. Includes built-in example plugins and demonstrates full functionality.

## Corrected Code
No correction needed.