from celery import Celery

celery = Celery(
    "opspilot",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)