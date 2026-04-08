import re
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass
class ConfigEntry:
    __slots__ = ('section', 'key', 'value')
    section: str
    key: str
    value: str


class ConfigParser:
    _re_section = re.compile(r'^\[(.+)\]$')
    _re_keyval = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._entries: list[ConfigEntry] = []
        self._ordered_sections: list[str] = []
        self._parse_text(text)

    def _parse_text(self, text: str) -> None:
        lines = text.split('\n')
        current = ''
        pos = 0
        while pos < len(lines):
            line = lines[pos].rstrip()
            clean = line.strip()
            if clean == '' or clean.startswith('#'):
                pos += 1
                continue
            sec_m = self._re_section.match(clean)
            if sec_m:
                current = sec_m.group(1)
                if current not in self._ordered_sections:
                    self._ordered_sections.append(current)
                pos += 1
                continue
            kv_m = self._re_keyval.match(clean)
            if kv_m:
                key_name = kv_m.group(1)
                val = kv_m.group(2)
                while val.endswith('\\'):
                    val = val[:-1]
                    pos += 1
                    if pos >= len(lines):
                        raise ConfigError('Unexpected end of file in multi-line value')
                    val += lines[pos].strip()
                entry = ConfigEntry(section=current, key=key_name, value=val)
                self._entries.append(entry)
                pos += 1
                continue
            raise ConfigError('Cannot parse line: ' + clean)

    def get(self, section: str, key: str) -> str:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                return entry.value
        raise ConfigError('No such key [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                entry.value = value
                return
        if section not in self._ordered_sections:
            self._ordered_sections.append(section)
        self._entries.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        for entry in self._entries:
            if entry.section == section and entry.key == key:
                return True
        return False

    def sections(self) -> list[str]:
        return list(self._ordered_sections)

    def to_dict(self) -> dict[str, dict[str, str]]:
        d: dict[str, dict[str, str]] = {}
        for entry in self._entries:
            sec = entry.section
            if sec not in d:
                d[sec] = {}
            d[sec][entry.key] = entry.value
        return d
