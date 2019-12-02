from celery import Celery

app = Celery('celery_tasks')
app.config_from_object('celery_tasks.celeryconfig')

app.autodiscover_tasks(['celery_tasks'])
