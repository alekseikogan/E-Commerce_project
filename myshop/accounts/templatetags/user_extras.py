from django import template

register = template.Library()


@register.filter
def user_initials(user):
    if not user.is_authenticated:
        return '?'

    first = (user.first_name or '').strip()
    last = (user.last_name or '').strip()

    if first and last:
        return f'{first[0]}{last[0]}'.upper()
    if first:
        return first[0].upper()
    if last:
        return last[0].upper()
    if user.username:
        return user.username[0].upper()
    return '?'
