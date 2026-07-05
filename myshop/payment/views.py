from decimal import Decimal

import stripe
from django.conf import settings
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render, reverse

from orders.models import Order, OrderItem

# создать экземпляр Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


def _order_from_master(order_id):
    """Заказ и позиции с master — сразу после создания на replica их может не быть."""
    return get_object_or_404(
        Order.objects.using('default').prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.using('default').select_related('product'),
            )
        ),
        id=order_id,
    )


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')


def payment_process(request):
    order_id = request.session.get('order_id')
    order = _order_from_master(order_id)

    if request.method == 'POST':
        success_url = request.build_absolute_uri(
            reverse('payment:completed')
        )
        cancel_url = request.build_absolute_uri(
            reverse('payment:canceled')
        )

        session_data = {
            'mode': 'payment',
            'client_reference_id': order.id,
            'success_url': success_url,
            'cancel_url': cancel_url,
            'line_items': []
        }

        # добавить товарные позиции заказа
        # в сеанс оформления платежа Stripe
        for item in order.items.all():
            session_data['line_items'].append({
                'price_data': {
                    'unit_amount': int(item.price * Decimal('100')),
                    'currency': 'rub',
                    'product_data': {
                        'name': item.product.name,
                    }},
                'quantity': item.quantity,
            })

        session = stripe.checkout.Session.create(**session_data)

        # перенаправить к платежной форме Stripe
        # стр 461 с картами для оплаты
        return redirect(session.url, code=303)

    else:
        return render(request, 'payment/process.html', locals())
