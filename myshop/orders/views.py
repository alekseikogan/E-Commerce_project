import logging

import weasyprint
from cart.cart import Cart
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required

from orders.tasks import order_created
from shop.kafka_events import publish_event

from .form import OrderCreateForm
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            if len(cart) == 0:
                return redirect('cart:cart_detail')

            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.save()
            items = []
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
                items.append({
                    'product_id': item['product'].id,
                    'product_slug': item['product'].slug,
                    'product_name': item['product'].name,
                    'quantity': item['quantity'],
                    'price': str(item['price']),
                })
            total_cost = str(cart.get_total_price())
            cart.clear()  # очистить корзину
            request.session['order_id'] = order.id  # сохранить номер заказа

            try:
                order_created.delay(order.id)  # пишет письмо
            except Exception:
                logger.exception(
                    'Failed to enqueue order notification for order %s',
                    order.id,
                )

            publish_event(
                'order.created',
                {
                    'order_id': order.id,
                    'user_id': order.user_id,
                    'email': order.email,
                    'items': items,
                    'items_count': len(items),
                    'total_cost': total_cost,
                },
                key=order.id,
            )

            return redirect(reverse('payment:process'))
    else:
        form = OrderCreateForm()

    return render(
        request,
        'orders/order/create.html',
        {'cart': cart, 'form': form},
    )


@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/order/pdf.html',
                            {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    weasyprint.HTML(string=html).write_pdf(response,
                                           stylesheets=[weasyprint.CSS(
                                               settings.STATIC_ROOT / 'css/pdf.css')])
    return response
