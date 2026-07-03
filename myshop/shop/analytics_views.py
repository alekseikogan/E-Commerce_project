import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from shop.clickhouse_client import query_dicts
from shop.kafka_events import publish_event

logger = logging.getLogger(__name__)

EVENT_LABELS = {
    'request.access': 'HTTP access',
    'page.viewed': 'Page view',
    'product.viewed': 'Product card',
    'cart.item_added': 'Cart add',
    'cart.item_removed': 'Cart remove',
    'order.created': 'Order created',
    'order.paid': 'Order paid',
    'user.click': 'Click',
}

ACTIVITY_PAGE_SIZE = 100


def _event_label(event_name):
    return EVENT_LABELS.get(event_name, event_name)


@staff_member_required
def analytics_dashboard(request):
    summary = query_dicts("""
        SELECT
            event,
            count() AS total
        FROM shop_events
        WHERE timestamp >= now() - INTERVAL 24 HOUR
        GROUP BY event
        ORDER BY total DESC
    """)

    hourly = query_dicts("""
        SELECT
            toStartOfHour(timestamp) AS hour,
            countIf(event = 'page.viewed') AS page_views,
            countIf(event = 'product.viewed') AS product_views,
            countIf(event = 'cart.item_added') AS cart_adds,
            countIf(event = 'order.created') AS orders,
            countIf(event = 'user.click') AS clicks
        FROM shop_events
        WHERE timestamp >= now() - INTERVAL 24 HOUR
        GROUP BY hour
        ORDER BY hour
    """)

    top_products = query_dicts("""
        SELECT
            product_name,
            product_id,
            count() AS views
        FROM shop_events
        WHERE event = 'product.viewed'
          AND timestamp >= now() - INTERVAL 7 DAY
          AND product_name != ''
        GROUP BY product_name, product_id
        ORDER BY views DESC
        LIMIT 10
    """)

    funnel = query_dicts("""
        SELECT
            countIf(event = 'page.viewed') AS page_views,
            countIf(event = 'product.viewed') AS product_views,
            countIf(event = 'cart.item_added') AS cart_adds,
            countIf(event = 'order.created') AS orders,
            countIf(event = 'order.paid') AS paid_orders
        FROM shop_events
        WHERE timestamp >= now() - INTERVAL 7 DAY
    """)

    activity_total_rows = query_dicts('SELECT count() AS total FROM shop_events')
    activity_total = activity_total_rows[0]['total'] if activity_total_rows else 0

    page_number = request.GET.get('page', 1)
    paginator = Paginator(range(activity_total), ACTIVITY_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)
    offset = (page_obj.number - 1) * ACTIVITY_PAGE_SIZE

    activity = query_dicts(f"""
        SELECT
            timestamp,
            event,
            user_id,
            session_key,
            path,
            page,
            element_text,
            product_name,
            order_id,
            method,
            status_code
        FROM shop_events
        ORDER BY timestamp DESC
        LIMIT {ACTIVITY_PAGE_SIZE} OFFSET {offset}
    """)

    totals = {row['event']: row['total'] for row in summary}
    funnel_row = funnel[0] if funnel else {}

    for row in summary:
        row['label'] = _event_label(row['event'])

    context = {
        'summary': summary,
        'totals': totals,
        'hourly': hourly,
        'top_products': top_products,
        'funnel': funnel_row,
        'activity': activity,
        'page_obj': page_obj,
        'activity_total': activity_total,
        'event_labels': EVENT_LABELS,
        'grafana_url': settings.GRAFANA_URL,
        'kpi': {
            'page_views': totals.get('page.viewed', 0),
            'product_views': totals.get('product.viewed', 0),
            'cart_adds': totals.get('cart.item_added', 0),
            'orders': totals.get('order.created', 0),
            'clicks': totals.get('user.click', 0),
            'access': totals.get('request.access', 0),
        },
    }
    return render(request, 'shop/analytics/dashboard.html', context)


@csrf_exempt
@require_POST
def track_clicks(request):
    raw_body = request.POST.get('payload')
    if raw_body is None:
        raw_body = request.body.decode('utf-8', errors='replace').strip()
    if not raw_body:
        return JsonResponse({'ok': False, 'error': 'empty body'}, status=400)

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    events = payload if isinstance(payload, list) else payload.get('events', [])
    if not isinstance(events, list):
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    user = request.user
    session_key = request.session.session_key or ''
    if not session_key:
        request.session.save()
        session_key = request.session.session_key or ''

    base = {
        'user_id': user.pk if user.is_authenticated else None,
        'session_key': session_key,
        'path': request.path,
        'page': payload.get('page', '') if isinstance(payload, dict) else '',
    }

    published = 0
    for item in events[:20]:
        if not isinstance(item, dict):
            continue
        publish_event(
            'user.click',
            {
                **base,
                'path': item.get('path', base['path']),
                'page': item.get('page', base['page']),
                'element': item.get('element', ''),
                'element_text': item.get('text', '')[:200],
                'href': item.get('href', '')[:500],
            },
            key=session_key or item.get('path'),
        )
        published += 1

    if published:
        logger.info('Collected %s click(s) from %s', published, request.META.get('REMOTE_ADDR'))

    return JsonResponse({'ok': True})
