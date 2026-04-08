You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use Python with standard library only.
2. Do NOT import or use the configparser, json, or yaml modules. Parse the config format manually using string operations and re module.
3. Do NOT use plain dict to store configuration data internally. Use NamedTuple or a dataclass with __slots__ for structured config storage.
4. All public methods must have complete type annotations (parameters and return types).
5. Define and raise a custom ConfigError exception for malformed input.
6. Implement as a single class in a single .py file.

Include:
1. Config format parsing strategy (string/regex, NOT configparser)
2. Internal data storage design (NamedTuple/dataclass, NOT plain dict)
3. Section and key management
4. Multi-line value handling
5. Error handling with ConfigError
6. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Write a Python class `ConfigParser` that parses a simple config format: key=value pairs (one per line), # comments (ignore), [section] headers, multi-line values using backslash continuation (line ending with \ continues to next line). Support methods: get(section, key) -> str, set(section, key, value), has(section, key) -> bool, sections() -> list[str], to_dict() -> dict. Raise ConfigError for malformed input.
