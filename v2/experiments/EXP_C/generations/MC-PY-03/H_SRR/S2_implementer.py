"""MC-PY-03: Template Engine — regex parsing, variables, conditionals, loops, filters"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Custom exception ────────────────────────────────────────────────

class TemplateSyntaxError(Exception):
    """Raised when template syntax is invalid."""

    def __init__(self, message: str, line: int | None = None, col: int | None = None) -> None:
        self.line = line
        self.col = col
        loc = f" (line {line})" if line else ""
        super().__init__(f"TemplateSyntaxError{loc}: {message}")


# ── AST-like node types ─────────────────────────────────────────────

@dataclass
class TextNode:
    text: str


@dataclass
class VarNode:
    expression: str
    filters: list[str] = field(default_factory=list)


@dataclass
class IfNode:
    condition: str
    true_body: list[Any]
    false_body: list[Any] = field(default_factory=list)


@dataclass
class ForNode:
    var_name: str
    iterable_expr: str
    body: list[Any]


Node = TextNode | VarNode | IfNode | ForNode

# ── Regex patterns ──────────────────────────────────────────────────

RE_VAR = re.compile(r"\{\{\s*(.+?)\s*\}\}")
RE_BLOCK_OPEN = re.compile(r"\{%\s*(.+?)\s*%\}")
RE_IF = re.compile(r"if\s+(.+)")
RE_ELIF = re.compile(r"elif\s+(.+)")
RE_ELSE = re.compile(r"else")
RE_ENDIF = re.compile(r"endif")
RE_FOR = re.compile(r"for\s+(\w+)\s+in\s+(.+)")
RE_ENDFOR = re.compile(r"endfor")

# ── Built-in filters ────────────────────────────────────────────────

BUILTIN_FILTERS: dict[str, Callable[[Any], Any]] = {
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "capitalize": lambda v: str(v).capitalize(),
    "strip": lambda v: str(v).strip(),
    "title": lambda v: str(v).title(),
    "length": lambda v: len(v) if hasattr(v, "__len__") else 0,
    "default": lambda v: v if v else "",
    "escape": lambda v: html.escape(str(v)),
    "int": lambda v: int(v),
    "float": lambda v: float(v),
    "str": lambda v: str(v),
    "reverse": lambda v: v[::-1] if isinstance(v, (str, list)) else v,
    "sort": lambda v: sorted(v) if isinstance(v, list) else v,
    "first": lambda v: v[0] if v else None,
    "last": lambda v: v[-1] if v else None,
    "join": lambda v: ", ".join(str(x) for x in v) if isinstance(v, list) else str(v),
}


# ── Template Engine class ───────────────────────────────────────────

class TemplateEngine:
    """Lightweight template engine with variable substitution, conditionals, loops, and filters."""

    def __init__(self) -> None:
        self._filters: dict[str, Callable[[Any], Any]] = dict(BUILTIN_FILTERS)

    def register_filter(self, name: str, func: Callable[[Any], Any]) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    # ── Tokenization ────────────────────────────────────────────────

    def _tokenize(self, template: str) -> list[tuple[str, str]]:
        """Split template into (type, value) tokens."""
        tokens: list[tuple[str, str]] = []
        pattern = re.compile(r"(\{\{.+?\}\}|\{%.+?%\})", re.DOTALL)
        parts = pattern.split(template)

        for part in parts:
            if not part:
                continue
            if part.startswith("{{") and part.endswith("}}"):
                tokens.append(("var", part[2:-2].strip()))
            elif part.startswith("{%") and part.endswith("%}"):
                tokens.append(("block", part[2:-2].strip()))
            else:
                tokens.append(("text", part))

        return tokens

    # ── Parsing ─────────────────────────────────────────────────────

    def _parse(self, tokens: list[tuple[str, str]], pos: int = 0) -> tuple[list[Node], int]:
        nodes: list[Node] = []

        while pos < len(tokens):
            tok_type, tok_val = tokens[pos]

            if tok_type == "text":
                nodes.append(TextNode(tok_val))
                pos += 1

            elif tok_type == "var":
                parts = [p.strip() for p in tok_val.split("|")]
                expr = parts[0]
                filters = parts[1:]
                nodes.append(VarNode(expression=expr, filters=filters))
                pos += 1

            elif tok_type == "block":
                m_if = RE_IF.fullmatch(tok_val)
                m_for = RE_FOR.fullmatch(tok_val)
                m_endif = RE_ENDIF.fullmatch(tok_val)
                m_endfor = RE_ENDFOR.fullmatch(tok_val)
                m_else = RE_ELSE.fullmatch(tok_val)
                m_elif = RE_ELIF.fullmatch(tok_val)

                if m_endif or m_endfor or m_else or m_elif:
                    # These are handled by the caller
                    return nodes, pos

                elif m_if:
                    condition = m_if.group(1)
                    pos += 1
                    true_body, pos = self._parse(tokens, pos)

                    false_body: list[Node] = []
                    if pos < len(tokens):
                        _, val = tokens[pos]
                        if RE_ELIF.fullmatch(val):
                            m_el = RE_ELIF.fullmatch(val)
                            assert m_el
                            elif_cond = m_el.group(1)
                            pos += 1
                            elif_body, pos = self._parse(tokens, pos)
                            false_body = [IfNode(condition=elif_cond, true_body=elif_body)]
                        elif RE_ELSE.fullmatch(val):
                            pos += 1
                            false_body, pos = self._parse(tokens, pos)

                    # Expect endif
                    if pos < len(tokens):
                        _, val = tokens[pos]
                        if RE_ENDIF.fullmatch(val):
                            pos += 1
                        else:
                            raise TemplateSyntaxError(f"Expected endif, got: {val}")
                    else:
                        raise TemplateSyntaxError("Unexpected end of template — missing endif")

                    nodes.append(IfNode(condition=condition, true_body=true_body, false_body=false_body))

                elif m_for:
                    var_name = m_for.group(1)
                    iterable_expr = m_for.group(2)
                    pos += 1
                    body, pos = self._parse(tokens, pos)

                    if pos < len(tokens):
                        _, val = tokens[pos]
                        if RE_ENDFOR.fullmatch(val):
                            pos += 1
                        else:
                            raise TemplateSyntaxError(f"Expected endfor, got: {val}")
                    else:
                        raise TemplateSyntaxError("Unexpected end of template — missing endfor")

                    nodes.append(ForNode(var_name=var_name, iterable_expr=iterable_expr, body=body))

                else:
                    raise TemplateSyntaxError(f"Unknown block tag: {tok_val}")

            else:
                pos += 1

        return nodes, pos

    # ── Evaluation ──────────────────────────────────────────────────

    def _eval_expr(self, expr: str, context: dict[str, Any]) -> Any:
        """Evaluate a simple expression in the given context."""
        try:
            safe_globals: dict[str, Any] = {"__builtins__": {"len": len, "range": range, "str": str, "int": int, "float": float, "bool": bool, "list": list, "True": True, "False": False, "None": None}}
            return eval(expr, safe_globals, context)
        except Exception:
            return ""

    def _apply_filters(self, value: Any, filter_names: list[str]) -> Any:
        for fname in filter_names:
            fn = self._filters.get(fname)
            if fn:
                try:
                    value = fn(value)
                except Exception:
                    pass
        return value

    def _render_nodes(self, nodes: list[Node], context: dict[str, Any]) -> str:
        parts: list[str] = []

        for node in nodes:
            if isinstance(node, TextNode):
                parts.append(node.text)

            elif isinstance(node, VarNode):
                val = self._eval_expr(node.expression, context)
                val = self._apply_filters(val, node.filters)
                parts.append(str(val))

            elif isinstance(node, IfNode):
                cond_result = self._eval_expr(node.condition, context)
                if cond_result:
                    parts.append(self._render_nodes(node.true_body, context))
                else:
                    parts.append(self._render_nodes(node.false_body, context))

            elif isinstance(node, ForNode):
                iterable = self._eval_expr(node.iterable_expr, context)
                if iterable and hasattr(iterable, "__iter__"):
                    for item in iterable:
                        loop_ctx = {**context, node.var_name: item}
                        parts.append(self._render_nodes(node.body, loop_ctx))

        return "".join(parts)

    # ── Public API ──────────────────────────────────────────────────

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Render a template string with the given context."""
        if context is None:
            context = {}
        tokens = self._tokenize(template)
        nodes, _ = self._parse(tokens)
        return self._render_nodes(nodes, context)

    def render_file(self, path: str, context: dict[str, Any] | None = None) -> str:
        """Render a template from a file."""
        from pathlib import Path as P
        content = P(path).read_text(encoding="utf-8")
        return self.render(content, context)


# ── Demo / self-test ────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    tpl = """Hello, {{ name | upper }}!
{% if is_admin %}You are an admin.{% else %}You are a regular user.{% endif %}

Items:
{% for item in items %}  - {{ item | capitalize }}
{% endfor %}
Total: {{ items | length }} items.
"""

    output = engine.render(tpl, {
        "name": "alice",
        "is_admin": False,
        "items": ["apple", "banana", "cherry"],
    })
    print(output)
