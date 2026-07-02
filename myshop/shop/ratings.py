from django.conf import settings
from django.db import transaction

from orders.models import OrderItem

from .models import Product, ProductStats

DEFAULT_WEIGHTS = {
    'views': 1,
    'cart_adds': 3,
    'orders': 10,
    'paid': 20,
}


def get_weights():
    return {
        **DEFAULT_WEIGHTS,
        **getattr(settings, 'PRODUCT_POPULARITY_WEIGHTS', {}),
    }


def recalculate_score(stats):
    weights = get_weights()
    stats.popularity_score = (
        stats.views_count * weights['views']
        + stats.cart_adds_count * weights['cart_adds']
        + stats.orders_count * weights['orders']
        + stats.paid_count * weights['paid']
    )


def bump_counter(product_id, field):
    if not Product.objects.filter(pk=product_id).exists():
        return

    with transaction.atomic():
        stats, _ = ProductStats.objects.select_for_update().get_or_create(
            product_id=product_id,
            defaults={
                'views_count': 0,
                'cart_adds_count': 0,
                'orders_count': 0,
                'paid_count': 0,
                'popularity_score': 0,
            },
        )
        setattr(stats, field, getattr(stats, field) + 1)
        recalculate_score(stats)
        stats.save(
            update_fields=[
                field,
                'popularity_score',
                'updated',
            ]
        )


def apply_event(payload):
    event = payload.get('event')
    if event == 'product.viewed':
        bump_counter(payload['product_id'], 'views_count')
    elif event == 'cart.item_added':
        bump_counter(payload['product_id'], 'cart_adds_count')
    elif event == 'order.created':
        for item in payload.get('items', []):
            bump_counter(item['product_id'], 'orders_count')
    elif event == 'order.paid':
        for order_item in OrderItem.objects.filter(order_id=payload['order_id']):
            bump_counter(order_item.product_id, 'paid_count')
