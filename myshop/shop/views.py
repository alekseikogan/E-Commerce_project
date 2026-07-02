from django.db.models import IntegerField, Value
from django.db.models.functions import Coalesce
from cart.forms import CartAddProductForm
from django.shortcuts import get_object_or_404, render

from .kafka_events import publish_event
from .models import Category, Product


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = (
        Product.objects.filter(available=True)
        .select_related('category', 'stats')
        .annotate(
            popularity=Coalesce(
                'stats__popularity_score',
                Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by('-popularity', 'name')
    )

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(
        request,
        'shop/product/list.html',
        {'category': category,
         'categories': categories,
         'products': products}
    )


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    cart_product_form = CartAddProductForm()

    publish_event(
        'product.viewed',
        {
            'product_id': product.id,
            'product_slug': product.slug,
            'product_name': product.name,
            'user_id': request.user.pk if request.user.is_authenticated else None,
            'session_key': request.session.session_key,
        },
        key=product.id,
    )

    return render(
        request,
        'shop/product/detail.html',
        {'product': product,
         'cart_product_form': cart_product_form}
        )
