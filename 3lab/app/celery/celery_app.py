from app.core.endpoints import FastApiServerInfo
from celery import Celery



celery_app = Celery(
    "lab3",
    broker=FastApiServerInfo.REDIS_BROKER,
    backend=FastApiServerInfo.REDIS_BACKEND,
)

# Определяю то, в каком формате отправлять и принимать запросы
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
)

# Передаю все "тяжелые" процессы которые выполняются на celery + redis
celery_app.autodiscover_tasks(['app.celery.tasks'])