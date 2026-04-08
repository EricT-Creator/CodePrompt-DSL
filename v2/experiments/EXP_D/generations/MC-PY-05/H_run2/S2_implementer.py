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
    SEC_RE = re.compile(r'^\[(.+)\]$')
    PAIR_RE = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._data: list[ConfigEntry] = []
        self._sec_list: list[str] = []
        self._read(text)

    def _read(self, raw: str) -> None:
        lines = raw.split('\n')
        sec = ''
        n = 0
        while n < len(lines):
            stripped = lines[n].rstrip().strip()
            if stripped == '' or stripped.startswith('#'):
                n += 1
                continue
            sm = self.SEC_RE.match(stripped)
            if sm:
                sec = sm.group(1)
                if sec not in self._sec_list:
                    self._sec_list.append(sec)
                n += 1
                continue
            km = self.PAIR_RE.match(stripped)
            if km:
                name = km.group(1)
                val = km.group(2)
                while val.endswith('\\'):
                    val = val[:-1]
                    n += 1
                    if n >= len(lines):
                        raise ConfigError('Unterminated multi-line value')
                    val += lines[n].strip()
                self._data.append(ConfigEntry(section=sec, key=name, value=val))
                n += 1
                continue
            raise ConfigError('Invalid line: ' + stripped)

    def get(self, section: str, key: str) -> str:
        for item in self._data:
            if item.section == section and item.key == key:
                return item.value
        raise ConfigError('Missing: [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for item in self._data:
            if item.section == section and item.key == key:
                item.value = value
                return
        if section not in self._sec_list:
            self._sec_list.append(section)
        self._data.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        return any(item.section == section and item.key == key for item in self._data)

    def sections(self) -> list[str]:
        return list(self._sec_list)

    def to_dict(self) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for item in self._data:
            result.setdefault(item.section, {})[item.key] = item.value
        return result
