import re
from typing import Any, Callable
from dataclasses import dataclass

class TemplateSyntaxError(Exception):
    def __init__(self, message: str, position: int = 0):
        self.message = message
        self.position = position
        super().__init__(f"Template syntax error at position {position}: {message}")

@dataclass
class TextNode:
    content: str

@dataclass
class VarNode:
    name: str
    filters: list[str]

@dataclass
class IfNode:
    condition: str
    body: list[Any]

@dataclass
class ForNode:
    var_name: str
    iterable_name: str
    body: list[Any]

FILTERS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
}

class TemplateEngine:
    TOKEN_PATTERN = re.compile(
        r'(\{\{.*?\}\}|\{%\s*if\s+.*?%\}|\{%\s*endif\s*%\}|\{%\s*for\s+.*?%\}|\{%\s*endfor\s*%\})',
        re.DOTALL
    )
    VAR_PATTERN = re.compile(r'\{\{\s*(\w+(?:\|\w+)*)\s*\}\}')
    IF_PATTERN = re.compile(r'\{%\s*if\s+(.+?)\s*%\}')
    FOR_PATTERN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}')
    
    def __init__(self, template: str):
        self.template = template
        self.ast = self._parse()
    
    def _tokenize(self) -> list[tuple[str, Any]]:
        tokens = []
        last_end = 0
        
        for match in self.TOKEN_PATTERN.finditer(self.template):
            if match.start() > last_end:
                tokens.append(("TEXT", self.template[last_end:match.start()]))
            
            token = match.group(1)
            
            if self.VAR_PATTERN.match(token):
                var_match = self.VAR_PATTERN.match(token)
                expr = var_match.group(1)
                parts = expr.split('|')
                tokens.append(("VAR", (parts[0], parts[1:])))
            elif self.IF_PATTERN.match(token):
                if_match = self.IF_PATTERN.match(token)
                tokens.append(("IF_OPEN", if_match.group(1)))
            elif re.match(r'\{%\s*endif\s*%\}', token):
                tokens.append(("ENDIF", None))
            elif self.FOR_PATTERN.match(token):
                for_match = self.FOR_PATTERN.match(token)
                tokens.append(("FOR_OPEN", (for_match.group(1), for_match.group(2))))
            elif re.match(r'\{%\s*endfor\s*%\}', token):
                tokens.append(("ENDFOR", None))
            else:
                raise TemplateSyntaxError(f"Unknown token: {token}", match.start())
            
            last_end = match.end()
        
        if last_end < len(self.template):
            tokens.append(("TEXT", self.template[last_end:]))
        
        return tokens
    
    def _parse(self) -> list[Any]:
        tokens = self._tokenize()
        root: list[Any] = []
        stack: list[Any] = [root]
        
        for i, (token_type, token_data) in enumerate(tokens):
            current = stack[-1]
            
            if token_type == "TEXT":
                current.append(TextNode(content=token_data))
            elif token_type == "VAR":
                name, filters = token_data
                current.append(VarNode(name=name, filters=filters))
            elif token_type == "IF_OPEN":
                node = IfNode(condition=token_data, body=[])
                current.append(node)
                stack.append(node.body)
            elif token_type == "FOR_OPEN":
                var_name, iterable_name = token_data
                node = ForNode(var_name=var_name, iterable_name=iterable_name, body=[])
                current.append(node)
                stack.append(node.body)
            elif token_type == "ENDIF":
                if len(stack) <= 1:
                    raise TemplateSyntaxError("Unexpected {% endif %}", i)
                popped = stack.pop()
                parent = stack[-1]
                if parent and isinstance(parent[-1], IfNode):
                    parent[-1].body = popped
                else:
                    raise TemplateSyntaxError("Mismatched {% endif %}", i)
            elif token_type == "ENDFOR":
                if len(stack) <= 1:
                    raise TemplateSyntaxError("Unexpected {% endfor %}", i)
                popped = stack.pop()
                parent = stack[-1]
                if parent and isinstance(parent[-1], ForNode):
                    parent[-1].body = popped
                else:
                    raise TemplateSyntaxError("Mismatched {% endfor %}", i)
        
        if len(stack) > 1:
            raise TemplateSyntaxError("Unclosed block", 0)
        
        return root
    
    def render(self, context: dict[str, Any]) -> str:
        return self._render_nodes(self.ast, context)
    
    def _render_nodes(self, nodes: list[Any], context: dict[str, Any]) -> str:
        result = []
        for node in nodes:
            result.append(self._render_node(node, context))
        return ''.join(result)
    
    def _render_node(self, node: Any, context: dict[str, Any]) -> str:
        if isinstance(node, TextNode):
            return node.content
        elif isinstance(node, VarNode):
            return self._render_var(node, context)
        elif isinstance(node, IfNode):
            return self._render_if(node, context)
        elif isinstance(node, ForNode):
            return self._render_for(node, context)
        return ''
    
    def _render_var(self, node: VarNode, context: dict[str, Any]) -> str:
        if node.name not in context:
            return ''
        value = str(context[node.name])
        for filter_name in node.filters:
            if filter_name not in FILTERS:
                raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
            value = FILTERS[filter_name](value)
        return value
    
    def _render_if(self, node: IfNode, context: dict[str, Any]) -> str:
        condition_value = context.get(node.condition)
        if condition_value:
            return self._render_nodes(node.body, context)
        return ''
    
    def _render_for(self, node: ForNode, context: dict[str, Any]) -> str:
        iterable = context.get(node.iterable_name)
        if not iterable:
            return ''
        if not hasattr(iterable, '__iter__'):
            raise TemplateSyntaxError(f"'{node.iterable_name}' is not iterable")
        result = []
        for item in iterable:
            child_context = {**context, node.var_name: item}
            result.append(self._render_nodes(node.body, child_context))
        return ''.join(result)
