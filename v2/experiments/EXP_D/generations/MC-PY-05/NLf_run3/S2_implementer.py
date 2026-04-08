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
    _rxsec = re.compile(r'^\[(.+)\]$')
    _rxkv = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._config: list[ConfigEntry] = []
        self._section_list: list[str] = []
        self._parse_input(text)

    def _parse_input(self, raw_text: str) -> None:
        lines = raw_text.split('\n')
        cur = ''
        idx = 0
        while idx < len(lines):
            trimmed = lines[idx].strip()
            if trimmed == '' or trimmed.startswith('#'):
                idx += 1
                continue
            sm = self._rxsec.match(trimmed)
            if sm:
                cur = sm.group(1)
                if cur not in self._section_list:
                    self._section_list.append(cur)
                idx += 1
                continue
            km = self._rxkv.match(trimmed)
            if km:
                the_key = km.group(1)
                the_value = km.group(2)
                while the_value.endswith('\\'):
                    the_value = the_value[:-1]
                    idx += 1
                    if idx >= len(lines):
                        raise ConfigError('EOF in multi-line continuation')
                    the_value += lines[idx].strip()
                self._config.append(ConfigEntry(section=cur, key=the_key, value=the_value))
                idx += 1
                continue
            raise ConfigError('Parse error at: ' + trimmed)

    def get(self, section: str, key: str) -> str:
        for c in self._config:
            if c.section == section and c.key == key:
                return c.value
        raise ConfigError('Cannot find [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for c in self._config:
            if c.section == section and c.key == key:
                c.value = value
                return
        if section not in self._section_list:
            self._section_list.append(section)
        self._config.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        for c in self._config:
            if c.section == section and c.key == key:
                return True
        return False

    def sections(self) -> list[str]:
        return list(self._section_list)

    def to_dict(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for c in self._config:
            if c.section not in out:
                out[c.section] = {}
            out[c.section][c.key] = c.value
        return out
