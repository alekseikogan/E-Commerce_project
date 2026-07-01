from cart.forms import CartAddProductForm
from django.shortcuts import get_object_or_404, render
from orders.tasks import process_number, what_time_is_it

from .models import Category, Product


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

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
    process_number.delay(5)
    for i in range(10):
        what_time_is_it.delay()

    return render(
        request,
        'shop/product/detail.html',
        {'product': product,
         'cart_product_form': cart_product_form}
        )
