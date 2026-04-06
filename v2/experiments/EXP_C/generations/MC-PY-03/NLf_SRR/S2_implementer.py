from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Exceptions ──────────────────────────────────────────────────────────

class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None, snippet: str = "") -> None:
        self.message = message
        self.line = line
        self.col = col
        self.snippet = snippet
        parts = [f"TemplateSyntaxError: {message}"]
        if line is not None:
            parts.append(f" at line {line}")
        if snippet:
            parts.append(f"\n  near: {snippet}")
        super().__init__("".join(parts))

    def to_dict(self) -> dict[str, Any]:
        return {"error": "TemplateSyntaxError", "message": self.message, "line": self.line, "col": self.col, "snippet": self.snippet}


# ── Filter registry ────────────────────────────────────────────────────

FilterFunc = Callable[..., Any]


class FilterRegistry:
    def __init__(self) -> None:
        self._filters: dict[str, FilterFunc] = {}
        self._register_builtins()

    def register(self, name: str, func: FilterFunc) -> None:
        self._filters[name] = func

    def get(self, name: str) -> FilterFunc | None:
        return self._filters.get(name)

    def apply(self, value: Any, name: str, args: list[str]) -> Any:
        fn = self.get(name)
        if fn is None:
            raise TemplateSyntaxError(f"Unknown filter: {name}")
        try:
            return fn(value, *args) if args else fn(value)
        except TemplateSyntaxError:
            raise
        except Exception as exc:
            raise TemplateSyntaxError(f"Filter '{name}' error: {exc}")

    def _register_builtins(self) -> None:
        self.register("upper", lambda v: str(v).upper())
        self.register("lower", lambda v: str(v).lower())
        self.register("capitalize", lambda v: str(v).capitalize())
        self.register("title", lambda v: str(v).title())
        self.register("strip", lambda v: str(v).strip())
        self.register("length", lambda v: len(v))
        self.register("default", lambda v, d="": d if v is None or v == "" else v)
        self.register("join", lambda v, sep=", ": sep.join(str(i) for i in v))
        self.register("reverse", lambda v: v[::-1] if isinstance(v, (str, list)) else v)
        self.register("int", lambda v: int(v))
        self.register("float", lambda v: float(v))
        self.register("str", lambda v: str(v))
        self.register("truncate", lambda v, n="80": str(v)[: int(n)])
        self.register("replace", lambda v, old, new="": str(v).replace(old, new))


# ── Regex patterns ──────────────────────────────────────────────────────

_VAR_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
_TAG_OPEN = re.compile(r"\{%\s*(.+?)\s*%\}")
_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


# ── Token types ─────────────────────────────────────────────────────────

class _TT:
    TEXT = "TEXT"
    VAR = "VAR"
    IF = "IF"
    ELIF = "ELIF"
    ELSE = "ELSE"
    ENDIF = "ENDIF"
    FOR = "FOR"
    ENDFOR = "ENDFOR"


@dataclass
class _Token:
    kind: str
    value: str
    line: int = 0


# ── Tokenizer ──────────────────────────────────────────────────────────

def _tokenize(template: str) -> list[_Token]:
    template = _COMMENT_RE.sub("", template)
    tokens: list[_Token] = []
    pos = 0

    def _lineno(p: int) -> int:
        return template[:p].count("\n") + 1

    combined = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)

    for m in combined.finditer(template):
        start, end = m.start(), m.end()
        if start > pos:
            tokens.append(_Token(_TT.TEXT, template[pos:start], _lineno(pos)))
        raw = m.group(0)
        ln = _lineno(start)

        if raw.startswith("{{"):
            inner = raw[2:-2].strip()
            tokens.append(_Token(_TT.VAR, inner, ln))
        elif raw.startswith("{%"):
            inner = raw[2:-2].strip()
            if inner.startswith("if "):
                tokens.append(_Token(_TT.IF, inner[3:].strip(), ln))
            elif inner.startswith("elif "):
                tokens.append(_Token(_TT.ELIF, inner[5:].strip(), ln))
            elif inner == "else":
                tokens.append(_Token(_TT.ELSE, "", ln))
            elif inner == "endif":
                tokens.append(_Token(_TT.ENDIF, "", ln))
            elif inner.startswith("for "):
                tokens.append(_Token(_TT.FOR, inner[4:].strip(), ln))
            elif inner == "endfor":
                tokens.append(_Token(_TT.ENDFOR, "", ln))
            else:
                raise TemplateSyntaxError(f"Unknown tag: {inner}", line=ln)
        pos = end

    if pos < len(template):
        tokens.append(_Token(_TT.TEXT, template[pos:], _lineno(pos)))
    return tokens


# ── AST nodes ───────────────────────────────────────────────────────────

@dataclass
class _TextNode:
    text: str

@dataclass
class _VarNode:
    expr: str
    filters: list[tuple[str, list[str]]]
    line: int = 0

@dataclass
class _IfNode:
    branches: list[tuple[str, list[Any]]]
    else_body: list[Any]

@dataclass
class _ForNode:
    item_var: str
    list_expr: str
    body: list[Any]


# ── Parser ──────────────────────────────────────────────────────────────

class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> _Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _next(self) -> _Token:
        t = self._tokens[self._pos]
        self._pos += 1
        return t

    def parse(self) -> list[Any]:
        return self._parse_body(set())

    def _parse_body(self, stop_kinds: set[str]) -> list[Any]:
        nodes: list[Any] = []
        while self._pos < len(self._tokens):
            t = self._peek()
            if t is None:
                break
            if t.kind in stop_kinds:
                break
            if t.kind == _TT.TEXT:
                self._next()
                nodes.append(_TextNode(t.value))
            elif t.kind == _TT.VAR:
                self._next()
                expr, filters = self._parse_var_expr(t.value)
                nodes.append(_VarNode(expr, filters, t.line))
            elif t.kind == _TT.IF:
                nodes.append(self._parse_if())
            elif t.kind == _TT.FOR:
                nodes.append(self._parse_for())
            else:
                raise TemplateSyntaxError(f"Unexpected tag: {t.kind}", line=t.line)
        return nodes

    def _parse_var_expr(self, raw: str) -> tuple[str, list[tuple[str, list[str]]]]:
        parts = raw.split("|")
        expr = parts[0].strip()
        filters: list[tuple[str, list[str]]] = []
        for p in parts[1:]:
            p = p.strip()
            if ":" in p:
                name, argstr = p.split(":", 1)
                args = [a.strip().strip("'\"") for a in argstr.split(",")]
            else:
                name, args = p, []
            filters.append((name.strip(), args))
        return expr, filters

    def _parse_if(self) -> _IfNode:
        t = self._next()
        cond = t.value
        body = self._parse_body({_TT.ELIF, _TT.ELSE, _TT.ENDIF})
        branches: list[tuple[str, list[Any]]] = [(cond, body)]
        else_body: list[Any] = []
        while True:
            nxt = self._peek()
            if nxt is None:
                raise TemplateSyntaxError("Unclosed if block")
            if nxt.kind == _TT.ELIF:
                self._next()
                eb = self._parse_body({_TT.ELIF, _TT.ELSE, _TT.ENDIF})
                branches.append((nxt.value, eb))
            elif nxt.kind == _TT.ELSE:
                self._next()
                else_body = self._parse_body({_TT.ENDIF})
                break
            elif nxt.kind == _TT.ENDIF:
                break
            else:
                raise TemplateSyntaxError(f"Unexpected token in if: {nxt.kind}", line=nxt.line)
        end = self._peek()
        if end is None or end.kind != _TT.ENDIF:
            raise TemplateSyntaxError("Missing endif")
        self._next()
        return _IfNode(branches, else_body)

    def _parse_for(self) -> _ForNode:
        t = self._next()
        m = re.match(r"(\w+)\s+in\s+(.+)", t.value)
        if not m:
            raise TemplateSyntaxError(f"Invalid for syntax: {t.value}", line=t.line)
        item_var = m.group(1)
        list_expr = m.group(2).strip()
        body = self._parse_body({_TT.ENDFOR})
        end = self._peek()
        if end is None or end.kind != _TT.ENDFOR:
            raise TemplateSyntaxError("Missing endfor")
        self._next()
        return _ForNode(item_var, list_expr, body)


# ── Evaluator ───────────────────────────────────────────────────────────

def _resolve(expr: str, context: dict[str, Any]) -> Any:
    parts = expr.split(".")
    val: Any = context
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        elif hasattr(val, p):
            val = getattr(val, p)
        else:
            return None
    return val


def _eval_condition(cond: str, context: dict[str, Any]) -> bool:
    cond = cond.strip()
    if cond.startswith("not "):
        return not _eval_condition(cond[4:], context)
    for op, fn in [(" == ", lambda a, b: a == b), (" != ", lambda a, b: a != b),
                   (" >= ", lambda a, b: a >= b), (" <= ", lambda a, b: a <= b),
                   (" > ", lambda a, b: a > b), (" < ", lambda a, b: a < b)]:
        if op in cond:
            left, right = cond.split(op, 1)
            lv = _resolve(left.strip(), context)
            rv = right.strip().strip("'\"")
            try:
                rv = type(lv)(rv) if lv is not None else rv
            except (ValueError, TypeError):
                pass
            return fn(lv, rv)
    val = _resolve(cond, context)
    return bool(val)


# ── Renderer ────────────────────────────────────────────────────────────

class _Renderer:
    def __init__(self, filters: FilterRegistry) -> None:
        self._filters = filters

    def render(self, nodes: list[Any], context: dict[str, Any]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, _TextNode):
                parts.append(node.text)
            elif isinstance(node, _VarNode):
                val = _resolve(node.expr, context)
                for fname, fargs in node.filters:
                    val = self._filters.apply(val, fname, fargs)
                parts.append("" if val is None else str(val))
            elif isinstance(node, _IfNode):
                rendered = False
                for cond, body in node.branches:
                    if _eval_condition(cond, context):
                        parts.append(self.render(body, context))
                        rendered = True
                        break
                if not rendered and node.else_body:
                    parts.append(self.render(node.else_body, context))
            elif isinstance(node, _ForNode):
                iterable = _resolve(node.list_expr, context)
                if iterable and hasattr(iterable, "__iter__"):
                    for item in iterable:
                        child_ctx = {**context, node.item_var: item}
                        parts.append(self.render(node.body, child_ctx))
        return "".join(parts)


# ── TemplateEngine ──────────────────────────────────────────────────────

class TemplateEngine:
    def __init__(self) -> None:
        self._filters: FilterRegistry = FilterRegistry()
        self._cache: dict[int, list[Any]] = {}

    def register_filter(self, name: str, func: FilterFunc) -> None:
        self._filters.register(name, func)

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        ctx = dict(context) if context else {}
        key = hash(template)
        if key not in self._cache:
            tokens = _tokenize(template)
            parser = _Parser(tokens)
            ast_nodes = parser.parse()
            self._cache[key] = ast_nodes
        renderer = _Renderer(self._filters)
        return renderer.render(self._cache[key], ctx)

    def render_file(self, path: str, context: dict[str, Any] | None = None) -> str:
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
        return self.render(template, context)

    def clear_cache(self) -> None:
        self._cache.clear()


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    tpl = """\
Hello, {{ name|upper }}!
{% if show_items %}Items:
{% for item in items %}- {{ item|capitalize }}
{% endfor %}{% else %}No items.{% endif %}
Total: {{ items|length }}"""

    result = engine.render(tpl, {
        "name": "world",
        "show_items": True,
        "items": ["apple", "banana", "cherry"],
    })
    print(result)
