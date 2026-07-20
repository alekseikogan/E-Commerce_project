import graphene

from orders.schema import Mutation as OrdersMutation
from orders.schema import Query as OrdersQuery
from shop.schema import Query as ShopQuery


class Query(ShopQuery, OrdersQuery, graphene.ObjectType):
    """Root Query: объединяет Query из приложений."""


class Mutation(OrdersMutation, graphene.ObjectType):
    """Root Mutation."""


schema = graphene.Schema(query=Query, mutation=Mutation)
