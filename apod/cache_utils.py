"""Cache keys, counters and invalidation helpers."""
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

PAGE_CACHE_PREFIX = "apodpage"


def apod_key(date_str):
    """Low-level cache key for one APOD date ('today' when no date given)."""
    return f"apod:{date_str or 'today'}"


def _incr(name):
    key = f"stats:{name}"
    cache.add(key, 0, None)  # no-op if it exists; never expires
    cache.incr(key)


def record_hit():
    _incr("hits")


def record_miss():
    _incr("misses")


def get_stats():
    hits = cache.get("stats:hits", 0)
    misses = cache.get("stats:misses", 0)
    total = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "hit_ratio": round(hits / total, 3) if total else None,
    }


def reset_stats():
    cache.delete_many(["stats:hits", "stats:misses"])


def key_ttl(date_str):
    """Seconds left on a key (None = no expiry, 0 = missing). Redis only."""
    if hasattr(cache, "ttl"):
        return cache.ttl(apod_key(date_str))
    return None


def invalidate_date(date_str):
    """Drop the low-level entry for one date, plus the per-view page cache."""
    cache.delete(apod_key(date_str))
    invalidate_page_cache()
    logger.info("invalidated cache for %s", date_str or "today")


def invalidate_all():
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("apod:*")
    else:
        cache.clear()
    invalidate_page_cache()
    logger.info("invalidated all apod cache entries")


def invalidate_page_cache():
    """Clear every @cache_page entry.

    cache_page builds keys from the full URL + headers, so we cannot cheaply
    rebuild the exact key for one date. Deleting by key prefix is coarse but
    safe. This is the 'invalidation is hard' trade-off in practice.
    """
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"*{PAGE_CACHE_PREFIX}*")
    else:
        cache.clear()
