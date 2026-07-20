import graphene
from graphene_django import DjangoObjectType

from .models import Category, Product


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'products')


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'price',
            'available',
            'created',
            'updated',
            'category',
        )


class Query(graphene.ObjectType):
    products = graphene.List(
        ProductType,
        available_only=graphene.Boolean(default_value=True),
        category_slug=graphene.String(required=False),
    )
    product = graphene.Field(ProductType, id=graphene.ID(required=True))
    categories = graphene.List(CategoryType)
    category = graphene.Field(
        CategoryType,
        slug=graphene.String(required=True),
    )

    def resolve_products(self, info, available_only=True, category_slug=None):
        qs = Product.objects.select_related('category')
        if available_only:
            qs = qs.filter(available=True)
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def resolve_product(self, info, id):
        try:
            return Product.objects.select_related('category').get(pk=id)
        except Product.DoesNotExist:
            return None

    def resolve_categories(self, info):
        return Category.objects.prefetch_related('products')

    def resolve_category(self, info, slug):
        try:
            return Category.objects.prefetch_related('products').get(slug=slug)
        except Category.DoesNotExist:
            return None
