"""Template handling for the project dumper."""

# Try to import pybars, but make it optional
try:
    from pybars import Compiler
    HAS_PYBARS = True
except ImportError:
    HAS_PYBARS = False
    Compiler = None


def load_template(template_path: str) -> str:
    """Load a Handlebars template file."""
    if not template_path:
        # Default template with proper variable names
        return """Project Path: {{absolute_code_path}}

Source Tree:
```
{{source_tree}}
```

{{#each files}}
{{#if code}}
`{{path}}`:
{{{code}}}

{{/if}}
{{/each}}"""
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading template {template_path}: {e}")
        print("Using default template instead")
        return load_template(None)  # Fall back to default template


def render_template(template: str, context: dict) -> str:
    """Render a template with the given context."""
    if not HAS_PYBARS:
        # Fallback: simple string replacement for basic templates
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    compiler = Compiler()
    compiled = compiler.compile(template)
    return compiled(context)