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
    SECTION_PATTERN = re.compile(r'^\[(.+)\]$')
    KV_PATTERN = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._entries: list[ConfigEntry] = []
        self._sections_seen: list[str] = []
        self._do_parse(text)

    def _do_parse(self, text: str) -> None:
        lines = text.split('\n')
        section = ''
        idx = 0
        while idx < len(lines):
            raw_line = lines[idx].rstrip()
            trimmed = raw_line.strip()
            if not trimmed or trimmed.startswith('#'):
                idx += 1
                continue
            m_section = self.SECTION_PATTERN.match(trimmed)
            if m_section:
                section = m_section.group(1)
                if section not in self._sections_seen:
                    self._sections_seen.append(section)
                idx += 1
                continue
            m_kv = self.KV_PATTERN.match(trimmed)
            if m_kv:
                k = m_kv.group(1)
                v = m_kv.group(2)
                while v.endswith('\\'):
                    v = v[:-1]
                    idx += 1
                    if idx >= len(lines):
                        raise ConfigError('Unclosed multi-line continuation at end of input')
                    v += lines[idx].strip()
                self._entries.append(ConfigEntry(section=section, key=k, value=v))
                idx += 1
                continue
            raise ConfigError('Malformed line: %s' % trimmed)

    def get(self, section: str, key: str) -> str:
        for e in self._entries:
            if e.section == section and e.key == key:
                return e.value
        raise ConfigError('Not found: [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for e in self._entries:
            if e.section == section and e.key == key:
                e.value = value
                return
        if section not in self._sections_seen:
            self._sections_seen.append(section)
        self._entries.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        return any(e.section == section and e.key == key for e in self._entries)

    def sections(self) -> list[str]:
        return list(self._sections_seen)

    def to_dict(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for e in self._entries:
            if e.section not in out:
                out[e.section] = {}
            out[e.section][e.key] = e.value
        return out
