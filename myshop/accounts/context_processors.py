from django.conf import settings


def admin_tools(request):
    return {
        'flower_url': settings.FLOWER_URL,
        'rabbitmq_url': settings.RABBITMQ_MANAGEMENT_URL,
        'stripe_dashboard_url': settings.STRIPE_DASHBOARD_URL,
    }
