from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .elasticsearch_client import delete_product, index_product
from .models import Product


@receiver(post_save, sender=Product)
def product_saved(sender, instance, **kwargs):
    if instance.available:
        index_product(instance)
    else:
        delete_product(instance.id)


@receiver(post_delete, sender=Product)
def product_deleted(sender, instance, **kwargs):
    delete_product(instance.id)
