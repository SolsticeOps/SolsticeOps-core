from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def to_opacity(value):
    """Maps 0-100 to 0.4-1.0 opacity range for high contrast."""
    try:
        return (float(value) / 100.0) * 0.6 + 0.4
    except:
        return 0.4

@register.filter
def split_env(value):
    """Splits 'KEY=VALUE' string into (KEY, VALUE) tuple."""
    if '=' in value:
        return value.split('=', 1)
    return value, ''

@register.filter
def split_at_colon_last(value):
    """Splits string at last colon and returns the last part."""
    if ':' in value:
        return value.split(':')[-1]
    return value

@register.filter
def split_at_colon_first(value):
    """Splits string at first colon and returns the first part."""
    if ':' in value:
        return value.split(':', 1)[0]
    return value

@register.simple_tag
def call_method(obj, method_name, *args):
    method = getattr(obj, method_name, None)
    if callable(method):
        return method(*args)
    return None
