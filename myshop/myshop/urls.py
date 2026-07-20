from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from shop.analytics_views import analytics_dashboard, track_clicks

urlpatterns = [
    path('health/', lambda request: HttpResponse('ok'), name='health'),
    # GraphQL API (вне i18n — URL без /en/ /ru/)
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('analytics/', analytics_dashboard, name='analytics_dashboard'),
    path('e/', track_clicks, name='event_collect'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('payment/', include('payment.urls', namespace='payment')),
    path('', include('shop.urls', namespace='shop')),
)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT)
