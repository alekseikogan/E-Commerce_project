from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])


class ProductStats(models.Model):
    product = models.OneToOneField(
        Product,
        related_name='stats',
        on_delete=models.CASCADE,
    )
    views_count = models.PositiveIntegerField(default=0)
    cart_adds_count = models.PositiveIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    paid_count = models.PositiveIntegerField(default=0)
    popularity_score = models.PositiveIntegerField(default=0, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'product stats'
        verbose_name_plural = 'product stats'

    def __str__(self):
        return f'Stats for {self.product.name} (score={self.popularity_score})'
