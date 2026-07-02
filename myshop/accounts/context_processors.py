import os

from django.conf import settings


def admin_tools(request):
    return {
        'flower_url': settings.FLOWER_URL,
        'rabbitmq_url': settings.RABBITMQ_MANAGEMENT_URL,
        'stripe_dashboard_url': settings.STRIPE_DASHBOARD_URL,
        'kafka_ui_url': os.environ.get('KAFKA_UI_URL', 'http://localhost:8080'),
        'kafka_load_url': os.environ.get('KAFKA_LOAD_URL', 'http://localhost:8081'),
    }
