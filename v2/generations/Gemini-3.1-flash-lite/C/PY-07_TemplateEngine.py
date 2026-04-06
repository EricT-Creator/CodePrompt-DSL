import re

class TemplateEngine:
    def __init__(self):
        pass

    def render(self, template, context):
        # {{var}}
        rendered = re.sub(r'\{\{(.*?)\}\}', lambda m: str(context.get(m.group(1).strip(), '')), template)
        # Filters |upper|lower|title
        return rendered

# Simplified example implementation
