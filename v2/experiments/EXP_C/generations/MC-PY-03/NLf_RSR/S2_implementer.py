import re
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass


class TemplateSyntaxError(Exception):
    """Exception raised for template syntax errors."""
    def __init__(self, message: str, line: Optional[int] = None):
        self.line = line
        super().__init__(f"TemplateSyntaxError at line {line}: {message}" if line else f"TemplateSyntaxError: {message}")


@dataclass
class TextNode:
    """Raw text node."""
    content: str


@dataclass
class VarNode:
    """Variable node with optional filters."""
    name: str
    filters: List[str]


@dataclass
class IfNode:
    """Conditional node."""
    condition: str
    body: List[Any]
    else_body: List[Any]


@dataclass
class ForNode:
    """Loop node."""
    var_name: str
    iterable_name: str
    body: List[Any]


@dataclass
class Template:
    """Root template container."""
    nodes: List[Any]


class TemplateEngine:
    """Template engine with regex parsing."""
    
    def __init__(self) -> None:
        """Initialize template engine with default filters."""
        self.filters: Dict[str, Callable[[str], str]] = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
        }
        
        self.patterns = {
            'var': re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*(?:\|[a-zA-Z_]+)*)\s*\}\}'),
            'if': re.compile(r'\{%\s*if\s+(.+?)\s*%\}'),
            'else': re.compile(r'\{%\s*else\s*%\}'),
            'endif': re.compile(r'\{%\s*endif\s*%\}'),
            'for': re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}'),
            'endfor': re.compile(r'\{%\s*endfor\s*%\}'),
            'any_tag': re.compile(r'\{\{.+?\}\}|\{%.+?%\}'),
        }
    
    def add_filter(self, name: str, func: Callable[[str], str]) -> None:
        """Add a custom filter."""
        self.filters[name] = func
    
    def tokenize(self, template: str) -> List[tuple[str, str, int]]:
        """Tokenize template into (type, content, position) tuples."""
        tokens: List[tuple[str, str, int]] = []
        pos = 0
        
        while pos < len(template):
            match = self.patterns['any_tag'].search(template, pos)
            
            if not match:
                text = template[pos:]
                if text.strip():
                    tokens.append(('TEXT', text, pos))
                break
            
            start = match.start()
            if start > pos:
                text = template[pos:start]
                if text.strip():
                    tokens.append(('TEXT', text, pos))
            
            tag = match.group()
            pos = match.end()
            
            if self.patterns['var'].match(tag):
                tokens.append(('VAR', tag, start))
            elif self.patterns['if'].match(tag):
                tokens.append(('IF', tag, start))
            elif self.patterns['else'].match(tag):
                tokens.append(('ELSE', tag, start))
            elif self.patterns['endif'].match(tag):
                tokens.append(('ENDIF', tag, start))
            elif self.patterns['for'].match(tag):
                tokens.append(('FOR', tag, start))
            elif self.patterns['endfor'].match(tag):
                tokens.append(('ENDFOR', tag, start))
            else:
                raise TemplateSyntaxError(f"Unknown tag: {tag}")
        
        return tokens
    
    def parse(self, template: str) -> Template:
        """Parse template into AST."""
        tokens = self.tokenize(template)
        nodes: List[Any] = []
        stack: List[Any] = []
        i = 0
        
        while i < len(tokens):
            token_type, content, pos = tokens[i]
            
            if token_type == 'TEXT':
                nodes.append(TextNode(content.strip()))
                i += 1
            
            elif token_type == 'VAR':
                var_match = self.patterns['var'].match(content)
                if not var_match:
                    raise TemplateSyntaxError(f"Invalid variable syntax: {content}")
                
                var_expr = var_match.group(1)
                if not var_expr:
                    raise TemplateSyntaxError(f"Empty variable: {content}")
                
                parts = var_expr.split('|')
                name = parts[0].strip()
                filters = [f.strip() for f in parts[1:]] if len(parts) > 1 else []
                
                for filter_name in filters:
                    if filter_name not in self.filters:
                        raise TemplateSyntaxError(f"Unknown filter: {filter_name}")
                
                nodes.append(VarNode(name, filters))
                i += 1
            
            elif token_type == 'IF':
                if_match = self.patterns['if'].match(content)
                if not if_match:
                    raise TemplateSyntaxError(f"Invalid if syntax: {content}")
                
                condition = if_match.group(1).strip()
                if_node = IfNode(condition, [], [])
                stack.append(('IF', if_node, nodes))
                nodes = if_node.body
                i += 1
            
            elif token_type == 'ELSE':
                if not stack or stack[-1][0] != 'IF':
                    raise TemplateSyntaxError("Unexpected else outside if block")
                
                _, if_node, _ = stack[-1]
                nodes = if_node.else_body
                i += 1
            
            elif token_type == 'ENDIF':
                if not stack or stack[-1][0] != 'IF':
                    raise TemplateSyntaxError("Unexpected endif without if")
                
                _, if_node, parent_nodes = stack.pop()
                parent_nodes.append(if_node)
                nodes = parent_nodes
                i += 1
            
            elif token_type == 'FOR':
                for_match = self.patterns['for'].match(content)
                if not for_match:
                    raise TemplateSyntaxError(f"Invalid for syntax: {content}")
                
                var_name = for_match.group(1).strip()
                iterable_name = for_match.group(2).strip()
                
                if not var_name or not iterable_name:
                    raise TemplateSyntaxError(f"Invalid for loop: {content}")
                
                for_node = ForNode(var_name, iterable_name, [])
                stack.append(('FOR', for_node, nodes))
                nodes = for_node.body
                i += 1
            
            elif token_type == 'ENDFOR':
                if not stack or stack[-1][0] != 'FOR':
                    raise TemplateSyntaxError("Unexpected endfor without for")
                
                _, for_node, parent_nodes = stack.pop()
                parent_nodes.append(for_node)
                nodes = parent_nodes
                i += 1
            else:
                i += 1
        
        if stack:
            block_type, _, _ = stack[-1]
            raise TemplateSyntaxError(f"Unclosed {block_type.lower()} block")
        
        return Template(nodes)
    
    def _resolve_variable(self, name: str, context: Dict[str, Any]) -> Any:
        """Resolve variable from context with dot notation."""
        parts = name.split('.')
        current = context
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            
            if current is None:
                return ''
        
        return current
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition string against context."""
        condition = condition.strip()
        
        if not condition:
            return False
        
        operators = ['==', '!=', '>=', '<=', '>', '<']
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._evaluate_condition(left.strip(), context)
                right_val = self._evaluate_condition(right.strip(), context)
                
                if op == '==':
                    return left_val == right_val
                elif op == '!=':
                    return left_val != right_val
                elif op == '>=':
                    return left_val >= right_val
                elif op == '<=':
                    return left_val <= right_val
                elif op == '>':
                    return left_val > right_val
                elif op == '<':
                    return left_val < right_val
        
        if condition.lower() == 'or':
            return True
        if condition.lower() == 'and':
            return True
        
        if ' or ' in condition.lower():
            parts = [p.strip() for p in condition.split(' or ')]
            return any(self._evaluate_condition(p, context) for p in parts)
        
        if ' and ' in condition.lower():
            parts = [p.strip() for p in condition.split(' and ')]
            return all(self._evaluate_condition(p, context) for p in parts)
        
        if condition.startswith('not '):
            return not self._evaluate_condition(condition[4:], context)
        
        value = self._resolve_variable(condition, context)
        return bool(value)
    
    def _apply_filters(self, value: Any, filters: List[str]) -> str:
        """Apply filter chain to value."""
        result = str(value)
        for filter_name in filters:
            if filter_name in self.filters:
                result = self.filters[filter_name](result)
        return result
    
    def _render_nodes(self, nodes: List[Any], context: Dict[str, Any]) -> str:
        """Render list of nodes."""
        result = []
        
        for node in nodes:
            if isinstance(node, TextNode):
                result.append(node.content)
            elif isinstance(node, VarNode):
                value = self._resolve_variable(node.name, context)
                result.append(self._apply_filters(value, node.filters))
            elif isinstance(node, IfNode):
                if self._evaluate_condition(node.condition, context):
                    result.append(self._render_nodes(node.body, context))
                elif node.else_body:
                    result.append(self._render_nodes(node.else_body, context))
            elif isinstance(node, ForNode):
                iterable = self._resolve_variable(node.iterable_name, context)
                if not iterable:
                    continue
                
                for item in iterable:
                    child_context = context.copy()
                    child_context[node.var_name] = item
                    result.append(self._render_nodes(node.body, child_context))
        
        return ''.join(result)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Parse and render template."""
        ast = self.parse(template)
        return self._render_nodes(ast.nodes, context)