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
    _sec_regex = re.compile(r'^\[(.+)\]$')
    _kv_regex = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._items: list[ConfigEntry] = []
        self._sec_order: list[str] = []
        self._interpret(text)

    def _interpret(self, input_text: str) -> None:
        lines = input_text.split('\n')
        section_name = ''
        line_idx = 0
        while line_idx < len(lines):
            current = lines[line_idx].strip()
            if current == '' or current.startswith('#'):
                line_idx += 1
                continue
            match_sec = self._sec_regex.match(current)
            if match_sec:
                section_name = match_sec.group(1)
                if section_name not in self._sec_order:
                    self._sec_order.append(section_name)
                line_idx += 1
                continue
            match_kv = self._kv_regex.match(current)
            if match_kv:
                parsed_key = match_kv.group(1)
                parsed_val = match_kv.group(2)
                while parsed_val.endswith('\\'):
                    parsed_val = parsed_val[:-1]
                    line_idx += 1
                    if line_idx >= len(lines):
                        raise ConfigError('Reached end of file during multi-line value')
                    parsed_val += lines[line_idx].strip()
                self._items.append(
                    ConfigEntry(section=section_name, key=parsed_key, value=parsed_val)
                )
                line_idx += 1
                continue
            raise ConfigError('Unparseable line: ' + current)

    def get(self, section: str, key: str) -> str:
        for item in self._items:
            if item.section == section and item.key == key:
                return item.value
        raise ConfigError('Entry [%s] %s not found' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for item in self._items:
            if item.section == section and item.key == key:
                item.value = value
                return
        if section not in self._sec_order:
            self._sec_order.append(section)
        self._items.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        for item in self._items:
            if item.section == section and item.key == key:
                return True
        return False

    def sections(self) -> list[str]:
        return list(self._sec_order)

    def to_dict(self) -> dict[str, dict[str, str]]:
        d: dict[str, dict[str, str]] = {}
        for item in self._items:
            if item.section not in d:
                d[item.section] = {}
            d[item.section][item.key] = item.value
        return d
