import time
from celery import shared_task

from django.core.mail import send_mail
from .models import Order


@shared_task
def order_created(order_id):
    """
    Задание по отправке уведомления по электронной почте
    при успешном создании заказа.
    """
    order = Order.objects.get(id=order_id)
    subject = f'Order nr. {order.id}'
    message = f'Dear {order.first_name},\n\n' \
        f'You have successfully placed an order.' \
        f'Your order ID is {order.id}.'

    mail_sent = send_mail(subject,
                          message,
                          'admin@yandex.ru',
                          [order.email])
    return mail_sent


@shared_task(queue='manual_queue')
def process_number(number=5):
    print(f"Начинаю обработку числа {number}...")
    time.sleep(5)  # имитация длительной операции
    print(f"Число {number} обработано!")
    return number * 2


@shared_task(queue='front_rubbish')
def what_time_is_it():
    print(f"Сколько времени??")
    time.sleep(10)  # имитация длительной операции
    print(f"Сейчас {time.strftime('%H:%M:%S')}")
    return time.strftime('%H:%M:%S')
