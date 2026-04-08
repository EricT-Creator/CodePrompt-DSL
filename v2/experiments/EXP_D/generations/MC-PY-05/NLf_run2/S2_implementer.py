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
    RE_SECTION = re.compile(r'^\[(.+)\]$')
    RE_KV = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._entries: list[ConfigEntry] = []
        self._section_names: list[str] = []
        self._process(text)

    def _process(self, source: str) -> None:
        lines = source.split('\n')
        active_section = ''
        cursor = 0
        while cursor < len(lines):
            raw = lines[cursor].strip()
            if raw == '' or raw.startswith('#'):
                cursor += 1
                continue
            sec_match = self.RE_SECTION.match(raw)
            if sec_match:
                active_section = sec_match.group(1)
                if active_section not in self._section_names:
                    self._section_names.append(active_section)
                cursor += 1
                continue
            kv_match = self.RE_KV.match(raw)
            if kv_match:
                k = kv_match.group(1)
                v = kv_match.group(2)
                while v.endswith('\\'):
                    v = v[:-1]
                    cursor += 1
                    if cursor >= len(lines):
                        raise ConfigError('Multi-line value not terminated')
                    v += lines[cursor].strip()
                self._entries.append(
                    ConfigEntry(section=active_section, key=k, value=v)
                )
                cursor += 1
                continue
            raise ConfigError('Bad line: ' + raw)

    def get(self, section: str, key: str) -> str:
        for e in self._entries:
            if e.section == section and e.key == key:
                return e.value
        raise ConfigError('[%s] %s does not exist' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for e in self._entries:
            if e.section == section and e.key == key:
                e.value = value
                return
        if section not in self._section_names:
            self._section_names.append(section)
        self._entries.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        return any(e.section == section and e.key == key for e in self._entries)

    def sections(self) -> list[str]:
        return list(self._section_names)

    def to_dict(self) -> dict[str, dict[str, str]]:
        output: dict[str, dict[str, str]] = {}
        for e in self._entries:
            output.setdefault(e.section, {})[e.key] = e.value
        return output
