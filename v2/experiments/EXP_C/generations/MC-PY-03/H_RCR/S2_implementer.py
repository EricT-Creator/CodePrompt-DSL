from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol, Union, runtime_checkable


class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        prefix = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")


@dataclass
class TextNode:
    text: str


@dataclass
class VarNode:
    var_name: str
    filters: List[str] = field(default_factory=list)


@dataclass
class IfNode:
    condition: str
    true_branch: List[Node] = field(default_factory=list)
    false_branch: List[Node] = field(default_factory=list)


@dataclass
class ForNode:
    loop_var: str
    iterable_name: str
    body: List[Node] = field(default_factory=list)


Node = Union[TextNode, VarNode, IfNode, ForNode]


class FilterRegistry:
    def __init__(self) -> None:
        self._filters: Dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize,
        }

    def apply(self, value: str, filter_names: List[str]) -> str:
        result = value
        for name in filter_names:
            if name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {name}")
            result = self._filters[name](result)
        return result

    def register(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func


class TemplateEngine:
    VAR_PATTERN = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_OPEN = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    ELSE_TAG = re.compile(r'\{%\s*else\s*%\}')
    ENDIF_TAG = re.compile(r'\{%\s*endif\s*%\}')
    FOR_OPEN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    ENDFOR_TAG = re.compile(r'\{%\s*endfor\s*%\}')
    TOKEN_PATTERN = re.compile(r'(\{\{.*?\}\}|\{%.*?%\})', re.DOTALL)

    def __init__(self) -> None:
        self._filter_registry = FilterRegistry()

    def _tokenize(self, template: str) -> List[tuple[str, str | None]]:
        parts = self.TOKEN_PATTERN.split(template)
        tokens: List[tuple[str, str | None]] = []

        for part in parts:
            if not part:
                continue
            if part.startswith('{{') and part.endswith('}}'):
                tokens.append(('var', part))
            elif part.startswith('{%') and part.endswith('%}'):
                if self.IF_OPEN.match(part):
                    tokens.append(('if_open', part))
                elif self.ELSE_TAG.match(part):
                    tokens.append(('else', part))
                elif self.ENDIF_TAG.match(part):
                    tokens.append(('endif', part))
                elif self.FOR_OPEN.match(part):
                    tokens.append(('for_open', part))
                elif self.ENDFOR_TAG.match(part):
                    tokens.append(('endfor', part))
                else:
                    raise TemplateSyntaxError(f"Invalid template tag: {part}")
            else:
                tokens.append(('text', part))

        return tokens

    def _parse_var(self, tag: str) -> VarNode:
        match = self.VAR_PATTERN.match(tag)
        if not match:
            raise TemplateSyntaxError(f"Invalid variable tag: {tag}")

        content = match.group(1)
        parts = content.split('|')
        var_name = parts[0].strip()
        filters = [f.strip() for f in parts[1:]]

        return VarNode(var_name=var_name, filters=filters)

    def _parse_if(self, tag: str) -> str:
        match = self.IF_OPEN.match(tag)
        if not match:
            raise TemplateSyntaxError(f"Invalid if tag: {tag}")
        return match.group(1).strip()

    def _parse_for(self, tag: str) -> tuple[str, str]:
        match = self.FOR_OPEN.match(tag)
        if not match:
            raise TemplateSyntaxError(f"Invalid for tag: {tag}")
        return match.group(1).strip(), match.group(2).strip()

    def _parse_tokens(self, tokens: List[tuple[str, str | None]]) -> List[Node]:
        root: List[Node] = []
        stack: List[List[Node]] = [root]
        if_stack: List[IfNode] = []
        for_stack: List[ForNode] = []

        i = 0
        while i < len(tokens):
            token_type, token_value = tokens[i]

            if token_type == 'text':
                node = TextNode(text=token_value or '')
                stack[-1].append(node)

            elif token_type == 'var':
                node = self._parse_var(token_value or '')
                stack[-1].append(node)

            elif token_type == 'if_open':
                condition = self._parse_if(token_value or '')
                node = IfNode(condition=condition)
                stack[-1].append(node)
                if_stack.append(node)
                stack.append(node.true_branch)

            elif token_type == 'else':
                if not if_stack:
                    raise TemplateSyntaxError("else without matching if")
                if_node = if_stack[-1]
                stack.pop()
                stack.append(if_node.false_branch)

            elif token_type == 'endif':
                if not if_stack:
                    raise TemplateSyntaxError("endif without matching if")
                if_stack.pop()
                stack.pop()

            elif token_type == 'for_open':
                loop_var, iterable_name = self._parse_for(token_value or '')
                node = ForNode(loop_var=loop_var, iterable_name=iterable_name)
                stack[-1].append(node)
                for_stack.append(node)
                stack.append(node.body)

            elif token_type == 'endfor':
                if not for_stack:
                    raise TemplateSyntaxError("endfor without matching for")
                for_stack.pop()
                stack.pop()

            i += 1

        if if_stack:
            raise TemplateSyntaxError("Unclosed if block")
        if for_stack:
            raise TemplateSyntaxError("Unclosed for block")

        return root

    def parse(self, template: str) -> List[Node]:
        tokens = self._tokenize(template)
        return self._parse_tokens(tokens)

    def _resolve_var(self, var_name: str, context: Dict[str, Any]) -> Any:
        if var_name in context:
            return context[var_name]
        raise TemplateSyntaxError(f"Undefined variable: {var_name}")

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        condition = condition.strip()

        if '==' in condition:
            left, right = condition.split('==', 1)
            left_val = self._resolve_var(left.strip(), context)
            right_val = right.strip().strip('"\'')
            return str(left_val) == right_val

        if '!=' in condition:
            left, right = condition.split('!=', 1)
            left_val = self._resolve_var(left.strip(), context)
            right_val = right.strip().strip('"\'')
            return str(left_val) != right_val

        val = self._resolve_var(condition, context)
        return bool(val)

    def _render_node(self, node: Node, context: Dict[str, Any]) -> str:
        if isinstance(node, TextNode):
            return node.text

        elif isinstance(node, VarNode):
            value = self._resolve_var(node.var_name, context)
            result = str(value)
            if node.filters:
                result = self._filter_registry.apply(result, node.filters)
            return result

        elif isinstance(node, IfNode):
            try:
                condition_result = self._eval_condition(node.condition, context)
            except TemplateSyntaxError:
                condition_result = False

            branch = node.true_branch if condition_result else node.false_branch
            return ''.join(self._render_node(n, context) for n in branch)

        elif isinstance(node, ForNode):
            iterable = self._resolve_var(node.iterable_name, context)
            if not isinstance(iterable, (list, tuple)):
                raise TemplateSyntaxError(f"{node.iterable_name} is not iterable")

            result = []
            for item in iterable:
                loop_context = dict(context)
                loop_context[node.loop_var] = item
                result.append(''.join(self._render_node(n, loop_context) for n in node.body))
            return ''.join(result)

        return ''

    def render(self, template: str, context: Dict[str, Any]) -> str:
        nodes = self.parse(template)
        return ''.join(self._render_node(n, context) for n in nodes)
