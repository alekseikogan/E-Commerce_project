import logging

from shop.kafka_events import publish_event

logger = logging.getLogger(__name__)

SKIP_PREFIXES = (
    '/static/',
    '/media/',
    '/favicon',
    '/e/',
)

SKIP_EXACT = (
    '/favicon.ico',
)


def _should_track(request):
    path = request.path
    if path in SKIP_EXACT:
        return False
    return not any(path.startswith(prefix) for prefix in SKIP_PREFIXES)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _page_name(request):
    match = getattr(request, 'resolver_match', None)
    if not match:
        return 'unknown'

    view_name = match.view_name or ''
    namespace = match.namespace or ''

    if view_name == 'shop:product_list' and not match.kwargs.get('category_slug'):
        return 'home'
    if view_name == 'shop:product_list':
        return 'catalog'
    if view_name == 'shop:product_detail':
        return 'product_detail'
    if view_name == 'cart:cart_detail':
        return 'cart'
    if view_name == 'orders:order_create':
        return 'checkout'
    if view_name == 'payment:process':
        return 'payment'
    if view_name == 'payment:completed':
        return 'payment_completed'
    if view_name == 'payment:canceled':
        return 'payment_canceled'
    if namespace == 'accounts':
        return f'accounts_{match.url_name}'
    if namespace == 'admin':
        return 'admin'

    return view_name.replace(':', '_') or 'unknown'


def _base_payload(request):
    user = request.user
    session_key = ''
    if hasattr(request, 'session'):
        session_key = request.session.session_key or ''
        if not session_key:
            request.session.save()
            session_key = request.session.session_key or ''

    return {
        'user_id': user.pk if getattr(user, 'is_authenticated', False) else None,
        'session_key': session_key,
        'path': request.path,
        'method': request.method,
        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
        'ip': _client_ip(request),
        'referer': request.META.get('HTTP_REFERER', '')[:500],
    }


class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not _should_track(request):
            return response

        payload = _base_payload(request)
        payload['status_code'] = response.status_code
        payload['page'] = _page_name(request)

        publish_event('request.access', payload, key=payload['session_key'] or payload['path'])

        if request.method == 'GET' and response.status_code < 400:
            content_type = response.get('Content-Type', '')
            if 'text/html' in content_type:
                publish_event(
                    'page.viewed',
                    {
                        **payload,
                        'view_name': getattr(request.resolver_match, 'view_name', ''),
                    },
                    key=payload['session_key'] or payload['path'],
                )

        return response
