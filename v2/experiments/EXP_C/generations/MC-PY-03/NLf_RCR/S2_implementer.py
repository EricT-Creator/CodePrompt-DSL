import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class TemplateSyntaxError(Exception):
    def __init__(self, message: str, line: Optional[int] = None):
        self.line = line
        if line:
            super().__init__(f"TemplateSyntaxError at line {line}: {message}")
        else:
            super().__init__(f"TemplateSyntaxError: {message}")


@dataclass
class TextNode:
    content: str


@dataclass
class VarNode:
    name: str
    filters: List[str] = field(default_factory=list)


@dataclass
class IfNode:
    condition: str
    body: List[Any] = field(default_factory=list)
    else_body: List[Any] = field(default_factory=list)


@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: List[Any] = field(default_factory=list)


@dataclass
class Template:
    nodes: List[Any] = field(default_factory=list)


class TemplateEngine:
    def __init__(self) -> None:
        self._filters: Dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "capitalize": str.capitalize
        }
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        self._filters[name] = func
    
    def parse(self, template: str) -> Template:
        tokens = self._tokenize(template)
        nodes, remaining = self._parse_nodes(tokens)
        if remaining:
            raise TemplateSyntaxError(f"Unexpected tokens: {remaining[0]}")
        return Template(nodes=nodes)
    
    def _tokenize(self, template: str) -> List[tuple[str, Optional[str]]]:
        pattern = r'(\{\{.*?\}\}|\{%.*?%\})'
        parts = re.split(pattern, template)
        tokens: List[tuple[str, Optional[str]]] = []
        for part in parts:
            if not part:
                continue
            if part.startswith('{{') and part.endswith('}}'):
                tokens.append(('VAR', part[2:-2].strip()))
            elif part.startswith('{%') and part.endswith('%}'):
                inner = part[2:-2].strip()
                if inner.startswith('if '):
                    tokens.append(('IF', inner[3:].strip()))
                elif inner == 'else':
                    tokens.append(('ELSE', None))
                elif inner == 'endif':
                    tokens.append(('ENDIF', None))
                elif inner.startswith('for '):
                    match = re.match(r'(\w+)\s+in\s+(\w+)', inner[4:].strip())
                    if match:
                        tokens.append(('FOR', (match.group(1), match.group(2))))
                    else:
                        raise TemplateSyntaxError(f"Invalid for syntax: {inner}")
                elif inner == 'endfor':
                    tokens.append(('ENDFOR', None))
                else:
                    tokens.append(('TEXT', part))
            else:
                tokens.append(('TEXT', part))
        return tokens
    
    def _parse_nodes(self, tokens: List[tuple[str, Optional[str]]]) -> tuple[List[Any], List[tuple[str, Optional[str]]]]:
        nodes: List[Any] = []
        i = 0
        while i < len(tokens):
            token_type, token_value = tokens[i]
            if token_type == 'TEXT':
                nodes.append(TextNode(content=token_value or ''))
            elif token_type == 'VAR':
                var_parts = token_value.split('|')
                name = var_parts[0].strip()
                filters = [f.strip() for f in var_parts[1:]]
                nodes.append(VarNode(name=name, filters=filters))
            elif token_type == 'IF':
                condition = token_value or ''
                body_nodes, next_i = self._parse_if_body(tokens, i + 1)
                nodes.append(IfNode(condition=condition, body=body_nodes[0], else_body=body_nodes[1]))
                i = next_i
                continue
            elif token_type == 'FOR':
                var_name, iterable_name = token_value
                body_nodes, next_i = self._parse_for_body(tokens, i + 1)
                nodes.append(ForNode(var_name=var_name, iterable_name=iterable_name, body=body_nodes))
                i = next_i
                continue
            elif token_type in ('ENDIF', 'ENDFOR', 'ELSE'):
                return nodes, tokens[i:]
            i += 1
        return nodes, []
    
    def _parse_if_body(self, tokens: List[tuple[str, Optional[str]]], start: int) -> tuple[tuple[List[Any], List[Any]], int]:
        if_body, remaining = self._parse_nodes(tokens[start:])
        else_body: List[Any] = []
        if remaining and remaining[0][0] == 'ELSE':
            else_body, remaining = self._parse_nodes(remaining[1:])
        if not remaining or remaining[0][0] != 'ENDIF':
            raise TemplateSyntaxError("Missing {% endif %}")
        return (if_body, else_body), start + len(tokens[start:]) - len(remaining)
    
    def _parse_for_body(self, tokens: List[tuple[str, Optional[str]]], start: int) -> tuple[List[Any], int]:
        body, remaining = self._parse_nodes(tokens[start:])
        if not remaining or remaining[0][0] != 'ENDFOR':
            raise TemplateSyntaxError("Missing {% endfor %}")
        return body, start + len(tokens[start:]) - len(remaining)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        ast = self.parse(template)
        return self._render_nodes(ast.nodes, context)
    
    def _render_nodes(self, nodes: List[Any], context: Dict[str, Any]) -> str:
        result = []
        for node in nodes:
            if isinstance(node, TextNode):
                result.append(node.content)
            elif isinstance(node, VarNode):
                result.append(self._render_var(node, context))
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, context):
                    result.append(self._render_nodes(node.body, context))
                else:
                    result.append(self._render_nodes(node.else_body, context))
            elif isinstance(node, ForNode):
                iterable = self._resolve_variable(node.iterable_name, context)
                if iterable and hasattr(iterable, '__iter__'):
                    for item in iterable:
                        child_context = {**context, node.var_name: item}
                        result.append(self._render_nodes(node.body, child_context))
        return ''.join(result)
    
    def _render_var(self, node: VarNode, context: Dict[str, Any]) -> str:
        value = self._resolve_variable(node.name, context)
        result = str(value) if value is not None else ''
        for filter_name in node.filters:
            if filter_name not in self._filters:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            result = self._filters[filter_name](result)
        return result
    
    def _resolve_variable(self, name: str, context: Dict[str, Any]) -> Any:
        parts = name.split('.')
        value = context.get(parts[0])
        for part in parts[1:]:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
        return value
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        condition = condition.strip()
        if ' or ' in condition:
            parts = condition.split(' or ')
            return any(self._evaluate_condition(p, context) for p in parts)
        if ' and ' in condition:
            parts = condition.split(' and ')
            return all(self._evaluate_condition(p, context) for p in parts)
        if condition.startswith('not '):
            return not self._evaluate_condition(condition[4:], context)
        for op in ['>=', '<=', '!=', '==', '>', '<']:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._resolve_variable(left.strip(), context)
                right_val = self._resolve_variable(right.strip(), context)
                if right_val is None:
                    try:
                        right_val = int(right.strip())
                    except ValueError:
                        try:
                            right_val = float(right.strip())
                        except ValueError:
                            right_val = right.strip().strip('"\'')
                return self._compare(left_val, right_val, op)
        value = self._resolve_variable(condition, context)
        return bool(value)
    
    def _compare(self, left: Any, right: Any, op: str) -> bool:
        try:
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '>': return left > right
            if op == '<': return left < right
            if op == '>=': return left >= right
            if op == '<=': return left <= right
        except TypeError:
            return False
        return False


if __name__ == "__main__":
    engine = TemplateEngine()
    result = engine.render("Hello {{name}}!", {"name": "World"})
    print(result)
