import re
from dataclasses import dataclass
from typing import Optional


class ConfigError(Exception):
    pass


@dataclass
class ConfigEntry:
    __slots__ = ('section', 'key', 'value')
    section: str
    key: str
    value: str


class ConfigParser:
    _section_re = re.compile(r'^\[(.+)\]$')
    _kv_re = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._entries: list[ConfigEntry] = []
        self._section_order: list[str] = []
        self._parse(text)

    def _parse(self, text: str) -> None:
        lines = text.split('\n')
        current_section = ''
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            if stripped == '' or stripped.startswith('#'):
                i += 1
                continue
            section_match = self._section_re.match(stripped)
            if section_match:
                current_section = section_match.group(1)
                if current_section not in self._section_order:
                    self._section_order.append(current_section)
                i += 1
                continue
            kv_match = self._kv_re.match(stripped)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2)
                while value.endswith('\\'):
                    value = value[:-1]
                    i += 1
                    if i >= len(lines):
                        raise ConfigError('Unclosed multi-line value at EOF')
                    value += lines[i].strip()
                self._entries.append(ConfigEntry(
                    section=current_section,
                    key=key,
                    value=value,
                ))
                i += 1
                continue
            raise ConfigError('Malformed line: ' + stripped)

    def get(self, section: str, key: str) -> str:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                return entry.value
        raise ConfigError('Key not found: [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                entry.value = value
                return
        if section not in self._section_order:
            self._section_order.append(section)
        self._entries.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                return True
        return False

    def sections(self) -> list[str]:
        return list(self._section_order)

    def to_dict(self) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for entry in self._entries:
            if entry.section not in result:
                result[entry.section] = {}
            result[entry.section][entry.key] = entry.value
        return result
