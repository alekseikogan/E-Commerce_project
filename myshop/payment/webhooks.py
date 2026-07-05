import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from orders.models import Order
from shop.kafka_events import publish_event

from .tasks import payment_completed


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET)

    except ValueError:
        # Недопустимая полезная нагрузка
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Недопустимая подпись
        return HttpResponse(status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        if session.mode == 'payment' and session.payment_status == 'paid':
            try:
                order = Order.objects.using('default').get(
                    id=session.client_reference_id,
                )
            except Order.DoesNotExist:
                return HttpResponse(status=404)
            # пометить заказ как оплаченный
            order.paid = True
            order.stripe_id = session.payment_intent
            order.save()
            publish_event(
                'order.paid',
                {
                    'order_id': order.id,
                    'user_id': order.user_id,
                    'email': order.email,
                    'stripe_id': order.stripe_id,
                    'total_cost': str(order.get_total_cost()),
                },
                key=order.id,
            )
            # отправить уведомление о оплате
            payment_completed.delay(order.id)
    return HttpResponse(status=200)
