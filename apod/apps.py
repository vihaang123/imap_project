from django.apps import AppConfig


class ApodConfig(AppConfig):
    name = "apod"

    def ready(self):
        from . import signals  # noqa: F401  (registers invalidation handlers)
