from django.db import models


class APODOverride(models.Model):
    """Locally curated edit layered on top of NASA's APOD for one date.

    This is the "source" that can change under the cache. Saving or deleting a
    row triggers cache invalidation (see signals.py).
    """

    date = models.DateField(unique=True)
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date}: {self.title}"
