from .settings import *  # noqa: F401,F403
CACHE_LABEL = "in-memory (tests)"

# Tests use an in-process cache so no Redis is needed.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
