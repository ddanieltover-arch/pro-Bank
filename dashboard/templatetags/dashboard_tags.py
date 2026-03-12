from django import template

register = template.Library()

@register.filter
def filter_type(queryset, card_type):
    return queryset.filter(card_type=card_type)
