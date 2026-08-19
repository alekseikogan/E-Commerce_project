import logging

from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

logger = logging.getLogger(__name__)

_client = None
_index_ready = False

INDEX_SETTINGS = {
    'number_of_shards': 1,
    'number_of_replicas': 0,
}

INDEX_MAPPINGS = {
    'properties': {
        'id': {'type': 'integer'},
        'name': {'type': 'text'},
        'slug': {'type': 'keyword'},
        'description': {'type': 'text'},
        'price': {'type': 'float'},
        'available': {'type': 'boolean'},
        'category_id': {'type': 'integer'},
        'category_name': {'type': 'text'},
        'category_slug': {'type': 'keyword'},
    }
}


def _index_name():
    return settings.ELASTICSEARCH_PRODUCTS_INDEX


def get_client():
    global _client
    if _client is not None:
        return _client

    _client = Elasticsearch(
        f'http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}',
        request_timeout=5,
    )
    return _client


def ensure_index(recreate=False):
    global _index_ready
    if _index_ready and not recreate:
        return True

    try:
        client = get_client()
        index_name = _index_name()
        exists = bool(client.indices.exists(index=index_name))
        if recreate and exists:
            client.indices.delete(index=index_name)
            exists = False
        if not exists:
            client.indices.create(
                index=index_name,
                settings=INDEX_SETTINGS,
                mappings=INDEX_MAPPINGS,
            )
        _index_ready = True
        return True
    except Exception:
        logger.exception('Elasticsearch ensure_index failed')
        _index_ready = False
        return False


def product_document(product):
    category = getattr(product, 'category', None)
    return {
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'description': product.description or '',
        'price': float(product.price),
        'available': product.available,
        'category_id': category.id if category else None,
        'category_name': category.name if category else '',
        'category_slug': category.slug if category else '',
    }


def index_product(product):
    if not ensure_index():
        return False
    try:
        get_client().index(
            index=_index_name(),
            id=product.id,
            document=product_document(product),
            refresh=True,
        )
        return True
    except Exception:
        logger.exception('Elasticsearch index_product failed')
        return False


def delete_product(product_id):
    try:
        get_client().delete(
            index=_index_name(),
            id=product_id,
            ignore_status=404,
            refresh=True,
        )
        return True
    except Exception:
        logger.exception('Elasticsearch delete_product failed')
        return False


def search_product_ids(query, category_slug=None, size=50):
    """Return ranked product ids, or None if Elasticsearch is unavailable."""
    if not query or not query.strip():
        return None
    if not ensure_index():
        return None

    filters = [{'term': {'available': True}}]
    if category_slug:
        filters.append({'term': {'category_slug': category_slug}})

    try:
        response = get_client().search(
            index=_index_name(),
            query={
                'bool': {
                    'must': [
                        {
                            'multi_match': {
                                'query': query.strip(),
                                'fields': ['name^3', 'description', 'category_name'],
                                'fuzziness': 'AUTO',
                            }
                        }
                    ],
                    'filter': filters,
                }
            },
            size=size,
            source=False,
        )
        return [int(hit['_id']) for hit in response['hits']['hits']]
    except Exception:
        logger.exception('Elasticsearch search failed')
        return None


def reindex_products(recreate=False):
    from shop.models import Product

    if not ensure_index(recreate=recreate):
        return 0

    products = Product.objects.select_related('category').filter(available=True)
    actions = [
        {
            '_index': _index_name(),
            '_id': product.id,
            '_source': product_document(product),
        }
        for product in products
    ]
    if not actions:
        return 0

    try:
        success, _errors = bulk(get_client(), actions, refresh=True)
        return success
    except Exception:
        logger.exception('Elasticsearch reindex_products failed')
        return 0
