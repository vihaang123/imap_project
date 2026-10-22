import json
from datetime import date as date_cls

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import cache_utils
from .models import APODOverride
from .services import NasaError, build_payload

TTL = settings.APOD_CACHE_TTL


def _parse_date(request):
    raw = request.GET.get("date")
    if not raw:
        return None, None
    try:
        date_cls.fromisoformat(raw)
    except ValueError:
        return None, JsonResponse({"error": "date must be YYYY-MM-DD"}, status=400)
    return raw, None


def apod_uncached(request):
    """Baseline: every request calls NASA."""
    date_str, err = _parse_date(request)
    if err:
        return err
    try:
        payload = build_payload(date_str)
    except NasaError as exc:
        return JsonResponse({"error": str(exc)}, status=exc.status)
    resp = JsonResponse(payload)
    resp["X-Cache"] = "BYPASS"
    return resp


def apod_low_level(request):
    """Low-level cache API: we decide the key, TTL and what gets stored."""
    date_str, err = _parse_date(request)
    if err:
        return err
    key = cache_utils.apod_key(date_str)
    payload = cache.get(key)
    if payload is not None:
        cache_utils.record_hit()
        resp = JsonResponse(payload)
        resp["X-Cache"] = "HIT"
        return resp
    cache_utils.record_miss()
    try:
        payload = build_payload(date_str)
    except NasaError as exc:
        # errors are never cached
        return JsonResponse({"error": str(exc)}, status=exc.status)
    cache.set(key, payload, TTL)
    resp = JsonResponse(payload)
    resp["X-Cache"] = "MISS"
    return resp


@cache_page(TTL, key_prefix=cache_utils.PAGE_CACHE_PREFIX)
def _apod_page_cached_inner(request):
    """Only runs on a page-cache miss. Django stores the whole response."""
    request._apod_generated = True
    return apod_uncached(request)


def apod_page_cached(request):
    """Per-view cache: Django caches the whole response keyed by URL.

    @cache_page replays the stored headers on a hit, so the stored response
    would always claim it was fresh. If the inner view never ran for this
    request, the response came from the cache, so we label it HIT ourselves.
    """
    resp = _apod_page_cached_inner(request)
    if resp.status_code == 200:
        resp["X-Cache"] = "MISS" if getattr(request, "_apod_generated", False) else "HIT"
    return resp


@csrf_exempt
@require_http_methods(["POST"])
def invalidate(request):
    """POST /api/cache/invalidate/?date=YYYY-MM-DD  (no date = clear all)."""
    date_str, err = _parse_date(request)
    if err:
        return err
    if date_str:
        cache_utils.invalidate_date(date_str)
        return JsonResponse({"invalidated": date_str})
    cache_utils.invalidate_all()
    return JsonResponse({"invalidated": "all"})


@csrf_exempt
@require_http_methods(["POST"])
def set_override(request):
    """Demo helper: change the 'source' so invalidation can be shown.

    Body: {"date": "YYYY-MM-DD", "title": "...", "note": "..."}
    Saving the model fires the post_save signal which clears the cache.
    """
    try:
        body = json.loads(request.body or b"{}")
        day = date_cls.fromisoformat(body["date"])
        title = body["title"]
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "need JSON with date (YYYY-MM-DD) and title"}, status=400)
    obj, _ = APODOverride.objects.update_or_create(
        date=day, defaults={"title": title, "note": body.get("note", "")}
    )
    return JsonResponse({"saved": str(obj)})


@csrf_exempt
@require_http_methods(["POST"])
def reset_stats(request):
    cache_utils.reset_stats()
    return JsonResponse({"reset": True})


def dashboard(request):
    return render(
        request,
        "apod/dashboard.html",
        {
            "default_date": "2024-01-15",
            "ttl": TTL,
            "mock": settings.USE_MOCK_NASA,
            "cache_label": settings.CACHE_LABEL,
        },
    )


def stats(request):
    date_str, err = _parse_date(request)
    if err:
        return err
    data = cache_utils.get_stats()
    data["ttl_seconds_left"] = cache_utils.key_ttl(date_str)
    data["configured_ttl"] = TTL
    return JsonResponse(data)
