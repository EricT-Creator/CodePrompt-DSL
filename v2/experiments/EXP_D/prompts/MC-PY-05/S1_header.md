[L]Python [D]STDLIB_ONLY [!CFG]NO_CONFIGPARSER_JSON_YAML [!DICT]NAMEDTUPLE_OR_DATACLASS_STORAGE [TYPE]FULL_ANNOTATIONS [ERR]ConfigError [OUT]SINGLE_CLASS

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

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
