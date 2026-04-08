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
    _pat_sec = re.compile(r'^\[(.+)\]$')
    _pat_kv = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._store: list[ConfigEntry] = []
        self._sections_order: list[str] = []
        self._load(text)

    def _load(self, content: str) -> None:
        all_lines = content.split('\n')
        cur_sec = ''
        i = 0
        while i < len(all_lines):
            line = all_lines[i].strip()
            if line == '' or line.startswith('#'):
                i += 1
                continue
            m = self._pat_sec.match(line)
            if m:
                cur_sec = m.group(1)
                if cur_sec not in self._sections_order:
                    self._sections_order.append(cur_sec)
                i += 1
                continue
            m2 = self._pat_kv.match(line)
            if m2:
                the_key = m2.group(1)
                the_val = m2.group(2)
                while the_val.endswith('\\'):
                    the_val = the_val[:-1]
                    i += 1
                    if i >= len(all_lines):
                        raise ConfigError('Unexpected EOF in multi-line value')
                    the_val += all_lines[i].strip()
                self._store.append(
                    ConfigEntry(section=cur_sec, key=the_key, value=the_val)
                )
                i += 1
                continue
            raise ConfigError('Unrecognized line: ' + line)

    def get(self, section: str, key: str) -> str:
        for e in self._store:
            if e.section == section and e.key == key:
                return e.value
        raise ConfigError('Key [%s] %s not found' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for e in self._store:
            if e.section == section and e.key == key:
                e.value = value
                return
        if section not in self._sections_order:
            self._sections_order.append(section)
        self._store.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        for e in self._store:
            if e.section == section and e.key == key:
                return True
        return False

    def sections(self) -> list[str]:
        return list(self._sections_order)

    def to_dict(self) -> dict[str, dict[str, str]]:
        mapping: dict[str, dict[str, str]] = {}
        for e in self._store:
            if e.section not in mapping:
                mapping[e.section] = {}
            mapping[e.section][e.key] = e.value
        return mapping
