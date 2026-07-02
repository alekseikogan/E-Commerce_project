from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from shop.models import Product
from .cart import Cart
from .forms import CartAddProductForm
from shop.kafka_events import publish_event


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        cart.add(
            product=product,
            quantity=cd['quantity'],
            override_quantity=cd['override']
        )

        publish_event(
            'cart.item_added',
            {
                'product_id': product.id,
                'product_slug': product.slug,
                'product_name': product.name,
                'user_id': request.user.pk if request.user.is_authenticated else None,
                'session_key': request.session.session_key,
                'quantity': cd['quantity'],
                'override': cd['override'],
                'line_quantity': cart.cart[str(product.id)]['quantity'],
            },
            key=product.id,
        )

    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(
            initial={
                'quantity': item['quantity'],
                'override': True
            }
        )

    return render(request, 'cart/detail.html', {'cart': cart})
