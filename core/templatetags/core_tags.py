from django import template

register = template.Library()

@register.filter
def to_opacity(value):
    """Converts a percentage (0-100) to an opacity value (0-1)."""
    try:
        # Ensure value is a float and scale it
        opacity = float(value) / 100.0
        # Clamp between 0 and 1
        return max(0.0, min(1.0, opacity))
    except (ValueError, TypeError):
        return 0.0

@register.simple_tag
def call_method(obj, method_name, *args):
    method = getattr(obj, method_name, None)
    if callable(method):
        return method(*args)
    return None
