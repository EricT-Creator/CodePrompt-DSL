import re

class TemplateEngine:
    def __init__(self):
        self.filters = {
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'title': lambda s: s.title()
        }

    def render(self, template, context):
        # Substitute vars {{var|filter}}
        def sub_var(match):
            parts = match.group(1).split('|')
            val = context.get(parts[0].strip(), '')
            for f in parts[1:]: val = self.filters[f.strip()](str(val))
            return str(val)
        
        template = re.sub(r'\{\{(.*?)\}\}', sub_var, template)
        
        # Handle loops {% for item in list %}...{% endfor %}
        def sub_for(match):
            var_name, list_name, content = match.groups()
            items = context.get(list_name.strip(), [])
            return "".join([self.render(content, {**context, var_name.strip(): item}) for item in items])
            
        template = re.sub(r'\{% for (.*?) in (.*?) %\}(.*?)\{% endfor %\}', sub_for, template, flags=re.DOTALL)
        return template
