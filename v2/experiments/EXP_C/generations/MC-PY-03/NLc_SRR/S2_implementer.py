"""
MC-PY-03: Template Engine
Engineering Constraints: Python 3.10+, stdlib only. Regex parsing, no jinja2/mako.
No ast module. Full type annotations. TemplateSyntaxError on errors. Single file, class output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── Exceptions ──────────────────────────────────────────────────────────


class TemplateError(Exception):
    def __init__(self, message: str, position: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.position = position


class TemplateSyntaxError(TemplateError):
    def __init__(self, message: str, position: Optional[int] = None) -> None:
        super().__init__(f"Syntax error: {message}", position)


class VariableNotFoundError(TemplateError):
    pass


class FilterNotFoundError(TemplateError):
    pass


# ── AST Nodes ───────────────────────────────────────────────────────────


@dataclass
class TemplateNode:
    node_type: str  # "root", "text", "variable", "if", "for", "comment"
    content: str = ""
    children: List[TemplateNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: TemplateNode) -> None:
        self.children.append(child)


# ── Patterns ────────────────────────────────────────────────────────────

RE_TAG = re.compile(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.DOTALL)
RE_VAR = re.compile(r"\{\{\s*(.+?)\s*\}\}", re.DOTALL)
RE_IF = re.compile(r"\{%\s*if\s+(.+?)\s*%\}", re.DOTALL)
RE_ELIF = re.compile(r"\{%\s*elif\s+(.+?)\s*%\}", re.DOTALL)
RE_ELSE = re.compile(r"\{%\s*else\s*%\}", re.DOTALL)
RE_ENDIF = re.compile(r"\{%\s*endif\s*%\}", re.DOTALL)
RE_FOR = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}", re.DOTALL)
RE_ENDFOR = re.compile(r"\{%\s*endfor\s*%\}", re.DOTALL)
RE_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)

# ── Filter Registry ────────────────────────────────────────────────────


class FilterRegistry:
    def __init__(self) -> None:
        self._filters: Dict[str, Callable[..., Any]] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        self.register("upper", lambda v: str(v).upper())
        self.register("lower", lambda v: str(v).lower())
        self.register("capitalize", lambda v: str(v).capitalize())
        self.register("title", lambda v: str(v).title())
        self.register("strip", lambda v: str(v).strip())
        self.register("length", lambda v: len(v) if hasattr(v, "__len__") else 0)
        self.register("default", lambda v, d="": v if v else d)
        self.register("join", lambda v, sep=", ": sep.join(str(x) for x in v) if isinstance(v, list) else str(v))
        self.register("reverse", lambda v: v[::-1] if isinstance(v, (str, list)) else v)
        self.register("first", lambda v: v[0] if v else "")
        self.register("last", lambda v: v[-1] if v else "")
        self.register("replace", lambda v, old, new: str(v).replace(old, new))
        self.register("truncate", lambda v, n="50": str(v)[: int(n)] + ("..." if len(str(v)) > int(n) else ""))
        self.register("int", lambda v: int(v) if str(v).isdigit() else 0)
        self.register("float", lambda v: float(v) if v else 0.0)
        self.register("str", lambda v: str(v))

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._filters[name] = func

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        return self._filters.get(name)

    def apply_chain(self, value: Any, chain: List[Tuple[str, List[str]]]) -> Any:
        result = value
        for filter_name, args in chain:
            func = self.get(filter_name)
            if func is None:
                raise FilterNotFoundError(f"Filter not found: {filter_name}")
            try:
                result = func(result, *args) if args else func(result)
            except Exception:
                pass  # Skip failing filter, keep current value
        return result


# ── Parser ──────────────────────────────────────────────────────────────


class TemplateParser:
    def __init__(self) -> None:
        self._tokens: List[Tuple[str, str, int]] = []

    def parse(self, template: str) -> TemplateNode:
        self._tokenize(template)
        root = TemplateNode(node_type="root")
        self._build_tree(root, 0, len(self._tokens))
        return root

    def _tokenize(self, template: str) -> None:
        self._tokens = []
        pos = 0
        for m in RE_TAG.finditer(template):
            if pos < m.start():
                self._tokens.append(("text", template[pos : m.start()], pos))
            tag = m.group(0)
            tag_type = self._classify(tag)
            self._tokens.append((tag_type, tag, m.start()))
            pos = m.end()
        if pos < len(template):
            self._tokens.append(("text", template[pos:], pos))

    def _classify(self, tag: str) -> str:
        if tag.startswith("{#"):
            return "comment"
        if tag.startswith("{{"):
            return "variable"
        # Control tags
        if RE_IF.match(tag):
            return "if_start"
        if RE_ELIF.match(tag):
            return "elif"
        if RE_ELSE.match(tag):
            return "else"
        if RE_ENDIF.match(tag):
            return "if_end"
        if RE_FOR.match(tag):
            return "for_start"
        if RE_ENDFOR.match(tag):
            return "for_end"
        return "unknown"

    def _build_tree(self, parent: TemplateNode, start: int, end: int) -> None:
        i = start
        while i < end:
            ttype, content, pos = self._tokens[i]

            if ttype == "text":
                parent.add_child(TemplateNode(node_type="text", content=content))
                i += 1

            elif ttype == "variable":
                m = RE_VAR.match(content)
                expr = m.group(1).strip() if m else content
                parent.add_child(TemplateNode(node_type="variable", content=expr, metadata={"pos": pos}))
                i += 1

            elif ttype == "comment":
                i += 1  # skip comments

            elif ttype == "if_start":
                m = RE_IF.match(content)
                condition = m.group(1).strip() if m else ""
                # Find matching endif, collecting elif/else
                block_end, branches = self._find_if_block(i, end)
                if_node = TemplateNode(node_type="if", metadata={"condition": condition, "branches": branches, "pos": pos})
                parent.add_child(if_node)
                # Build children for each branch
                for branch in branches:
                    branch_node = TemplateNode(node_type="branch", metadata={"condition": branch["condition"]})
                    self._build_tree(branch_node, branch["start"], branch["end"])
                    if_node.add_child(branch_node)
                i = block_end + 1

            elif ttype == "for_start":
                m = RE_FOR.match(content)
                if not m:
                    raise TemplateSyntaxError(f"Invalid for tag: {content}", pos)
                item_var = m.group(1).strip()
                list_var = m.group(2).strip()
                block_end = self._find_block_end(i, "for_start", "for_end", end)
                for_node = TemplateNode(node_type="for", metadata={"item_var": item_var, "list_var": list_var, "pos": pos})
                self._build_tree(for_node, i + 1, block_end)
                parent.add_child(for_node)
                i = block_end + 1

            elif ttype in ("if_end", "for_end", "elif", "else"):
                # Should not encounter these at top level during tree building
                i += 1

            else:
                parent.add_child(TemplateNode(node_type="text", content=content))
                i += 1

    def _find_if_block(self, start: int, end: int) -> Tuple[int, List[Dict[str, Any]]]:
        """Returns (endif_index, list_of_branches) where each branch is {condition, start, end}."""
        depth = 0
        branches: List[Dict[str, Any]] = []
        m = RE_IF.match(self._tokens[start][1])
        current_condition = m.group(1).strip() if m else "True"
        current_start = start + 1

        for i in range(start, end):
            ttype = self._tokens[i][0]
            if ttype == "if_start":
                if i != start:
                    depth += 1
            elif ttype == "if_end":
                if depth == 0:
                    branches.append({"condition": current_condition, "start": current_start, "end": i})
                    return i, branches
                depth -= 1
            elif ttype == "elif" and depth == 0:
                branches.append({"condition": current_condition, "start": current_start, "end": i})
                m2 = RE_ELIF.match(self._tokens[i][1])
                current_condition = m2.group(1).strip() if m2 else "True"
                current_start = i + 1
            elif ttype == "else" and depth == 0:
                branches.append({"condition": current_condition, "start": current_start, "end": i})
                current_condition = "True"
                current_start = i + 1

        raise TemplateSyntaxError("Unclosed if block", self._tokens[start][2])

    def _find_block_end(self, start: int, open_type: str, close_type: str, end: int) -> int:
        depth = 0
        for i in range(start, end):
            ttype = self._tokens[i][0]
            if ttype == open_type:
                depth += 1
            elif ttype == close_type:
                depth -= 1
                if depth == 0:
                    return i
        raise TemplateSyntaxError(f"Unclosed {open_type} block", self._tokens[start][2])


# ── Renderer ────────────────────────────────────────────────────────────


class TemplateRenderer:
    def __init__(self, filters: Optional[FilterRegistry] = None) -> None:
        self.filters = filters or FilterRegistry()

    def render(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        parts: List[str] = []
        for child in node.children:
            parts.append(self._render_node(child, context))
        return "".join(parts)

    def _render_node(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        if node.node_type == "text":
            return node.content
        elif node.node_type == "variable":
            return self._render_variable(node.content, context)
        elif node.node_type == "if":
            return self._render_if(node, context)
        elif node.node_type == "for":
            return self._render_for(node, context)
        elif node.node_type == "root" or node.node_type == "branch":
            return "".join(self._render_node(c, context) for c in node.children)
        return ""

    def _render_variable(self, expr: str, context: Dict[str, Any]) -> str:
        # Parse filters: var_name|filter1|filter2:arg
        parts = expr.split("|")
        var_path = parts[0].strip()
        filter_chain: List[Tuple[str, List[str]]] = []

        for fp in parts[1:]:
            fp = fp.strip()
            if not fp:
                continue
            colon_parts = fp.split(":")
            fname = colon_parts[0].strip()
            fargs = [a.strip().strip("'\"") for a in colon_parts[1:]]
            filter_chain.append((fname, fargs))

        value = self._resolve(var_path, context)
        if filter_chain:
            value = self.filters.apply_chain(value, filter_chain)
        return str(value) if value is not None else ""

    def _resolve(self, path: str, context: Dict[str, Any]) -> Any:
        parts = path.split(".")
        current: Any = context
        for part in parts:
            part = part.strip()
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            if current is None:
                return None
        return current

    def _render_if(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        for branch in node.children:
            condition = branch.metadata.get("condition", "True")
            if self._eval_condition(condition, context):
                return "".join(self._render_node(c, context) for c in branch.children)
        return ""

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        resolved = self._resolve_condition_vars(condition, context)
        safe_ns: Dict[str, Any] = {
            "__builtins__": {},
            "len": len, "str": str, "int": int, "float": float, "bool": bool,
            "True": True, "False": False, "None": None,
        }
        try:
            return bool(eval(resolved, safe_ns))
        except Exception:
            return False

    def _resolve_condition_vars(self, expr: str, context: Dict[str, Any]) -> str:
        def replacer(m: re.Match[str]) -> str:
            path = m.group(0)
            val = self._resolve(path, context)
            return repr(val)
        # Match dotted identifiers that look like variable paths
        return re.sub(r"[a-zA-Z_]\w*(?:\.\w+)*", replacer, expr)

    def _render_for(self, node: TemplateNode, context: Dict[str, Any]) -> str:
        item_var = node.metadata["item_var"]
        list_var = node.metadata["list_var"]
        iterable = self._resolve(list_var, context)

        if not iterable or not hasattr(iterable, "__iter__"):
            return ""

        parts: List[str] = []
        items = list(iterable)
        for idx, item in enumerate(items):
            loop_ctx = {
                **context,
                item_var: item,
                "loop": {
                    "index": idx + 1,
                    "index0": idx,
                    "first": idx == 0,
                    "last": idx == len(items) - 1,
                    "length": len(items),
                },
            }
            for child in node.children:
                parts.append(self._render_node(child, loop_ctx))
        return "".join(parts)


# ── Main Engine ─────────────────────────────────────────────────────────


class TemplateEngine:
    def __init__(self) -> None:
        self.parser = TemplateParser()
        self.filters = FilterRegistry()
        self.renderer = TemplateRenderer(self.filters)
        self._cache: Dict[str, TemplateNode] = {}

    def render(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        if template not in self._cache:
            self._cache[template] = self.parser.parse(template)
        tree = self._cache[template]
        return self.renderer.render(tree, ctx)

    def register_filter(self, name: str, func: Callable[..., Any]) -> None:
        self.filters.register(name, func)

    def clear_cache(self) -> None:
        self._cache.clear()


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = TemplateEngine()

    template = """
Hello, {{ name | upper }}!

{% if show_list %}
Your items:
{% for item in items %}
  {{ loop.index }}. {{ item.name }} - ${{ item.price }}
{% endfor %}
Total items: {{ items | length }}
{% endif %}

{% if not show_list %}
No items to display.
{% endif %}

Footer: {{ footer | default:'No footer provided' }}
"""

    ctx = {
        "name": "Alice",
        "show_list": True,
        "items": [
            {"name": "Widget", "price": "9.99"},
            {"name": "Gadget", "price": "24.99"},
            {"name": "Doohickey", "price": "4.50"},
        ],
    }

    result = engine.render(template, ctx)
    print(result)
