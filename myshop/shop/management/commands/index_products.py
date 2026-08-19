from django.core.management.base import BaseCommand

from shop.elasticsearch_client import reindex_products


class Command(BaseCommand):
    help = 'Create the products index and reindex available products from Postgres'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Delete and recreate the Elasticsearch index before indexing',
        )

    def handle(self, *args, **options):
        count = reindex_products(recreate=options['recreate'])
        self.stdout.write(self.style.SUCCESS(f'Indexed {count} products'))
