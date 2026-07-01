import os

from celery import Celery

# Указывает Celery, где искать настройки Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
app = Celery('myshop')
# Загрузи настройки из Django settings.py, но только те, что начинаются с CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
