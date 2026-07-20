import logging

import graphene
from django.db import transaction
from graphene_django import DjangoObjectType

from orders.tasks import order_created
from shop.kafka_events import publish_event
from shop.models import Product

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'price', 'quantity')


class OrderType(DjangoObjectType):
    total_cost = graphene.Decimal()

    class Meta:
        model = Order
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'address',
            'postal_code',
            'city',
            'paid',
            'created',
            'items',
        )

    def resolve_total_cost(self, info):
        return self.get_total_cost()


class OrderItemInput(graphene.InputObjectType):
    product_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)


class CreateOrder(graphene.Mutation):
    class Arguments:
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        email = graphene.String(required=True)
        address = graphene.String(required=True)
        postal_code = graphene.String(required=True)
        city = graphene.String(required=True)
        items = graphene.List(graphene.NonNull(OrderItemInput), required=True)

    order = graphene.Field(OrderType)
    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        first_name,
        last_name,
        email,
        address,
        postal_code,
        city,
        items,
    ):
        errors = []
        if not items:
            return CreateOrder(ok=False, errors=['Cart is empty'], order=None)

        prepared = []
        for item in items:
            if item.quantity < 1:
                errors.append(
                    f'Invalid quantity for product {item.product_id}'
                )
                continue
            try:
                product = Product.objects.get(pk=item.product_id, available=True)
            except Product.DoesNotExist:
                errors.append(f'Product {item.product_id} not found')
                continue
            prepared.append((product, item.quantity))

        if errors:
            return CreateOrder(ok=False, errors=errors, order=None)
        if not prepared:
            return CreateOrder(ok=False, errors=['No valid items'], order=None)

        request = info.context
        with transaction.atomic():
            order = Order(
                first_name=first_name,
                last_name=last_name,
                email=email,
                address=address,
                postal_code=postal_code,
                city=city,
            )
            if getattr(request, 'user', None) and request.user.is_authenticated:
                order.user = request.user
            order.save()

            event_items = []
            for product, quantity in prepared:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=product.price,
                    quantity=quantity,
                )
                event_items.append({
                    'product_id': product.id,
                    'product_slug': product.slug,
                    'product_name': product.name,
                    'quantity': quantity,
                    'price': str(product.price),
                })

        total_cost = str(order.get_total_cost())

        try:
            order_created.delay(order.id)
        except Exception:
            logger.exception(
                'Failed to enqueue order notification for order %s',
                order.id,
            )

        publish_event(
            'order.created',
            {
                'order_id': order.id,
                'user_id': order.user_id,
                'email': order.email,
                'items': event_items,
                'items_count': len(event_items),
                'total_cost': total_cost,
            },
            key=order.id,
        )

        if hasattr(request, 'session'):
            request.session['order_id'] = order.id

        return CreateOrder(ok=True, errors=[], order=order)


class Mutation(graphene.ObjectType):
    create_order = CreateOrder.Field()


class Query(graphene.ObjectType):
    order = graphene.Field(OrderType, id=graphene.ID(required=True))

    def resolve_order(self, info, id):
        try:
            return Order.objects.prefetch_related('items__product').get(pk=id)
        except Order.DoesNotExist:
            return None
