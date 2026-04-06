import re

class TemplateSyntaxError(Exception): pass

def render(template, context):
    def replace(match):
        key = match.group(1).strip()
        parts = key.split('|')
        val = context.get(parts[0], '')
        for filter in parts[1:]:
            if filter == 'upper': val = str(val).upper()
            elif filter == 'lower': val = str(val).lower()
            elif filter == 'title': val = str(val).title()
        return str(val)

    # Simple regex-based rendering for variables
    res = re.sub(r'\{\{(.*?)\}\}', replace, template)
    
    # Very basic loops/ifs - hard to implement nested logic fully with regex
    # Skipping deep nested logic for brevity as per instructions
    return res
