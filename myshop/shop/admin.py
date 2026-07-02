from django.contrib import admin

from .models import Category, Product, ProductStats


class ProductStatsInline(admin.StackedInline):
    model = ProductStats
    extra = 0
    readonly_fields = [
        'views_count',
        'cart_adds_count',
        'orders_count',
        'paid_count',
        'popularity_score',
        'updated',
    ]
    can_delete = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'price',
        'available',
        'popularity_score',
        'created',
        'updated',
    ]
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductStatsInline]

    @admin.display(description='Popularity')
    def popularity_score(self, product):
        stats = getattr(product, 'stats', None)
        return stats.popularity_score if stats else 0


@admin.register(ProductStats)
class ProductStatsAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'popularity_score',
        'views_count',
        'cart_adds_count',
        'orders_count',
        'paid_count',
        'updated',
    ]
    list_filter = ['updated']
    search_fields = ['product__name', 'product__slug']
    readonly_fields = [
        'product',
        'views_count',
        'cart_adds_count',
        'orders_count',
        'paid_count',
        'popularity_score',
        'updated',
    ]
