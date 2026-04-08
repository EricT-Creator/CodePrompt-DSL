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
    SECTION_PAT = re.compile(r'^\[(.+)\]$')
    KV_PAT = re.compile(r'^(\w[\w.-]*)\s*=\s*(.*)$')

    def __init__(self, text: str) -> None:
        self._records: list[ConfigEntry] = []
        self._secs: list[str] = []
        self._scan(text)

    def _scan(self, txt: str) -> None:
        all_lines = txt.split('\n')
        active = ''
        ptr = 0
        while ptr < len(all_lines):
            ln = all_lines[ptr].strip()
            if ln == '' or ln.startswith('#'):
                ptr += 1
                continue
            s = self.SECTION_PAT.match(ln)
            if s:
                active = s.group(1)
                if active not in self._secs:
                    self._secs.append(active)
                ptr += 1
                continue
            kv = self.KV_PAT.match(ln)
            if kv:
                k_name = kv.group(1)
                k_val = kv.group(2)
                while k_val.endswith('\\'):
                    k_val = k_val[:-1]
                    ptr += 1
                    if ptr >= len(all_lines):
                        raise ConfigError('Premature EOF in multi-line value')
                    k_val += all_lines[ptr].strip()
                self._records.append(ConfigEntry(section=active, key=k_name, value=k_val))
                ptr += 1
                continue
            raise ConfigError('Unrecognized: ' + ln)

    def get(self, section: str, key: str) -> str:
        for rec in self._records:
            if rec.section == section and rec.key == key:
                return rec.value
        raise ConfigError('Not found [%s] %s' % (section, key))

    def set(self, section: str, key: str, value: str) -> None:
        for rec in self._records:
            if rec.section == section and rec.key == key:
                rec.value = value
                return
        if section not in self._secs:
            self._secs.append(section)
        self._records.append(ConfigEntry(section=section, key=key, value=value))

    def has(self, section: str, key: str) -> bool:
        return any(r.section == section and r.key == key for r in self._records)

    def sections(self) -> list[str]:
        return list(self._secs)

    def to_dict(self) -> dict[str, dict[str, str]]:
        res: dict[str, dict[str, str]] = {}
        for r in self._records:
            res.setdefault(r.section, {})[r.key] = r.value
        return res
