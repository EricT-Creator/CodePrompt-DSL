import re
from typing import Dict, Any, List

class TemplateSyntaxError(Exception):
    pass

class TemplateEngine:
    def __init__(self):
        self.variable_pattern = re.compile(r'\{\{\s*(\w+)\s*\}\}')
        self.filter_pattern = re.compile(r'^(\w+)\s*\|\s*(\w+)$')
        
    def apply_filter(self, value: Any, filter_name: str) -> str:
        str_value = str(value)
        if filter_name == 'upper':
            return str_value.upper()
        elif filter_name == 'lower':
            return str_value.lower()
        elif filter_name == 'title':
            return str_value.title()
        else:
            return str_value
    
    def parse_variable(self, expr: str, context: Dict[str, Any]) -> str:
        expr = expr.strip()
        filter_match = self.filter_pattern.match(expr)
        
        if filter_match:
            var_name = filter_match.group(1)
            filter_name = filter_match.group(2)
        else:
            var_name = expr
            filter_name = None
        
        if var_name not in context:
            return ''
        
        value = context[var_name]
        
        if filter_name:
            return self.apply_filter(value, filter_name)
        return str(value)
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        result = []
        i = 0
        
        while i < len(template):
            if template[i:i+2] == '{{':
                end = template.find('}}', i)
                if end == -1:
                    raise TemplateSyntaxError("Unclosed variable tag")
                expr = template[i+2:end].strip()
                result.append(self.parse_variable(expr, context))
                i = end + 2
            
            elif template[i:i+2] == '{%':
                end = template.find('%}', i)
                if end == -1:
                    raise TemplateSyntaxError("Unclosed control tag")
                
                tag_content = template[i+2:end].strip()
                
                if tag_content.startswith('if '):
                    condition = tag_content[3:].strip()
                    if_end = self.find_matching_endif(template, end + 2)
                    if if_end == -1:
                        raise TemplateSyntaxError("Missing endif")
                    
                    inner_template = template[end+2:if_end]
                    if condition in context and context[condition]:
                        result.append(self.render(inner_template, context))
                    i = if_end + len('{% endif %}')
                
                elif tag_content.startswith('for '):
                    for_match = re.match(r'for\s+(\w+)\s+in\s+(\w+)', tag_content)
                    if not for_match:
                        raise TemplateSyntaxError("Invalid for syntax")
                    
                    item_name = for_match.group(1)
                    list_name = for_match.group(2)
                    
                    for_end = self.find_matching_endfor(template, end + 2)
                    if for_end == -1:
                        raise TemplateSyntaxError("Missing endfor")
                    
                    inner_template = template[end+2:for_end]
                    
                    if list_name in context and isinstance(context[list_name], (list, tuple)):
                        for item in context[list_name]:
                            loop_context = dict(context)
                            loop_context[item_name] = item
                            result.append(self.render(inner_template, loop_context))
                    i = for_end + len('{% endfor %}')
                
                else:
                    raise TemplateSyntaxError(f"Unknown tag: {tag_content}")
            
            else:
                result.append(template[i])
                i += 1
        
        return ''.join(result)
    
    def find_matching_endif(self, template: str, start: int) -> int:
        depth = 1
        i = start
        while i < len(template) - 1:
            if template[i:i+2] == '{%':
                end = template.find('%}', i)
                if end == -1:
                    break
                tag = template[i+2:end].strip()
                if tag.startswith('if ') and not tag.startswith('if '):
                    depth += 1
                elif tag == 'endif':
                    depth -= 1
                    if depth == 0:
                        return i
                i = end + 2
            else:
                i += 1
        return -1
    
    def find_matching_endfor(self, template: str, start: int) -> int:
        depth = 1
        i = start
        while i < len(template) - 1:
            if template[i:i+2] == '{%':
                end = template.find('%}', i)
                if end == -1:
                    break
                tag = template[i+2:end].strip()
                if tag.startswith('for '):
                    depth += 1
                elif tag == 'endfor':
                    depth -= 1
                    if depth == 0:
                        return i
                i = end + 2
            else:
                i += 1
        return -1


def render(template: str, context: Dict[str, Any]) -> str:
    engine = TemplateEngine()
    return engine.render(template, context)


if __name__ == "__main__":
    template = """
Hello {{ name|title }}!
{% if show_items %}
Items:
{% for item in items %}
- {{ item|upper }}
{% endfor %}
{% endif %}
"""
    
    context = {
        "name": "john",
        "show_items": True,
        "items": ["apple", "banana", "cherry"]
    }
    
    print(render(template, context))
