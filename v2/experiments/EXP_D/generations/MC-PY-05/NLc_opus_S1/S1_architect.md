# Technical Design: Config File Parser

## Overview
Python class that parses INI-style config files using regex/string ops (no configparser module), storing data in structured types (no plain dict).

## Config Format
```
# This is a comment
[section_name]
key1 = value1
key2 = this is a \
       multi-line value
key3 = value3
```

## Internal Data Storage

Use a dataclass with __slots__ for each config entry:
```
@dataclass
class ConfigEntry:
    __slots__ = ('section', 'key', 'value')
    section: str
    key: str
    value: str
```

Store all entries in: `self._entries: list[ConfigEntry]`

Section lookup: iterate entries and filter by section. This avoids using a plain dict as the primary storage.

## Parsing Strategy

1. Read input text line by line
2. Strip comments: lines starting with # (after optional whitespace)
3. Track current section (default: "" for entries before any section header)
4. Section headers: match `re.compile(r'^\[(.+)\]$')` on stripped line
5. Key-value pairs: match `re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')` on stripped line
6. Multi-line continuation: if value ends with `\`, read next line and append (strip leading whitespace)
7. Raise ConfigError for malformed lines (not empty, not comment, not section, not key=value)

## Public API

- `__init__(self, text: str) -> None` — Parse on construction
- `get(self, section: str, key: str) -> str` — Return value or raise ConfigError
- `set(self, section: str, key: str, value: str) -> None` — Add/update entry
- `has(self, section: str, key: str) -> bool` — Check existence
- `sections(self) -> list[str]` — Return unique section names in order
- `to_dict(self) -> dict[str, dict[str, str]]` — Export as nested dict (output convenience, not internal storage)

## Error Handling

`class ConfigError(Exception)` — raised for:
- Malformed line that isn't comment/section/kv/blank
- get() for non-existent section/key
- Unclosed multi-line value at EOF

## Constraint Acknowledgment
- C1: Python stdlib only — no third-party imports
- C2: NO configparser/json/yaml — manual parsing with re and string ops
- C3: NO plain dict for internal config storage — use dataclass ConfigEntry with __slots__
- C4: Full type annotations on all public methods
- C5: ConfigError custom exception defined and raised
- C6: Single file with class
