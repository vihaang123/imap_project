from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache_utils import invalidate_date
from .models import APODOverride


@receiver([post_save, post_delete], sender=APODOverride)
def clear_cache_on_override_change(sender, instance, **kwargs):
    """Source changed -> throw away the stale cached copy."""
    # date may still be a str if the row was created with one; str() covers both
    invalidate_date(str(instance.date))
