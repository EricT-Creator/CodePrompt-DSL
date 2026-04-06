import re

class TemplateSyntaxError(Exception): pass

class TemplateEngine:
    def render(self, template, context):
        def replace_var(match):
            return str(context.get(match.group(1).strip(), ''))
        
        template = re.sub(r'\{\{(.*?)\}\}', replace_var, template)
        
        def replace_if(match):
            condition, content = match.groups()
            return content if context.get(condition.strip()) else ''
        
        template = re.sub(r'\{% if (.*?) %\}(.*?)\{% endif %\}', replace_if, template, flags=re.S)
        
        def replace_for(match):
            var, iterable, content = match.groups()
            return ''.join([content.replace(f'{{ {var} }}', str(item)) for item in context.get(iterable, [])])
        
        template = re.sub(r'\{% for (.*?) in (.*?) %\}(.*?)\{% endfor %\}', replace_for, template, flags=re.S)
        
        return template
